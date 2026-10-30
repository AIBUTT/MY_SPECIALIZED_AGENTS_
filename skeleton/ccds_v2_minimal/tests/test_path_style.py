import io
import json
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_DIRS = ("scripts", "{{module_name}}", "tests")
BACKSLASH = chr(92)
PATH_LITERAL = re.compile(
    r"(?<!\w)[A-Za-z]:\\|}\\[\w{]|" + re.escape(BACKSLASH * 2) + r"\w"
)


def path_violations(source: str, location: str) -> list[str]:
    source = "".join(
        "\n" if line.lstrip().startswith(("%", "!")) else line
        for line in source.splitlines(keepends=True)
    )
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    failures = []
    for token in tokens:
        if token.type != tokenize.STRING:
            continue
        prefix = re.match("[a-zA-Z]*", token.string).group().lower()
        for match in PATH_LITERAL.finditer(token.string):
            if (
                match.group().startswith("}" + BACKSLASH)
                and "r" not in prefix
                and match.group()[-1] in "abfnrtv"
            ):
                continue
            failures.append(f"{location}:{token.start[0]}: backslash path literal")
            break
    significant = [
        token for token in tokens
        if token.type in (tokenize.NAME, tokenize.OP, tokenize.STRING, tokenize.NUMBER)
    ]
    for index, token in enumerate(significant):
        sequence = [(item.type, item.string) for item in significant[index:index + 5]]
        os_prefix = [(tokenize.NAME, "os"), (tokenize.OP, ".")]
        if sequence[:3] == os_prefix + [(tokenize.NAME, "sep")]:
            failures.append(f"{location}:{token.start[0]}: os.sep")
        if (
            sequence[:4] == os_prefix + [(tokenize.NAME, "path"), (tokenize.OP, ".")]
            and len(sequence) == 5
            and sequence[4] != (tokenize.NAME, "relpath")
        ):
            failures.append(f"{location}:{token.start[0]}: os.path.{sequence[4][1]}")
    return failures


def test_detector_rejects_paths():
    source = "\n".join([
        'root = r"C:' + BACKSLASH + 'data"',
        'cache = rf"{ROOT}' + BACKSLASH + 'interim' + BACKSLASH + '{name}"',
        'output = "dir' + BACKSLASH * 2 + 'file"',
        "os.path.join(root, name)",
        "os.sep",
    ])
    failures = path_violations(source, "example.py")
    assert len(failures) == 5
    assert [failure.split(":")[1] for failure in failures] == ["1", "2", "3", "4", "5"]


def test_detector_allows_regexes_and_relpath():
    source = r'''
pattern = r"run_\d{2}"
frontmatter = r"\A---\s*\n(.*?)\n---\s*\n"
newline = "\n"
"""os.path.join and os.sep are forbidden."""
# os.path.join and os.sep
Path(os.path.relpath(target, start_dir)).as_posix()
%matplotlib inline
!pwd
'''
    source += 'formatted = f"{value}' + BACKSLASH + 'n"\n'
    assert path_violations(source, "example.py") == []


def test_detector_allows_colon_before_escape():
    source = r'''
message = "Validation failed:\n"
header = "\nData types:\n"
'''
    assert path_violations(source, "example.py") == []


def test_repository_path_style():
    failures = []
    for directory in CODE_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            failures.extend(path_violations(path.read_text(encoding="utf-8"),
                                            path.relative_to(ROOT).as_posix()))
    for path in sorted((ROOT / "notebooks").rglob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for number, cell in enumerate(notebook["cells"], start=1):
            if cell["cell_type"] == "code":
                location = f"{path.relative_to(ROOT).as_posix()} (cell {number})"
                failures.extend(path_violations("".join(cell["source"]), location))
    assert not failures, "\n" + "\n".join(failures)
