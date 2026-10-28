---
applyTo: ".github/**/*.md"
description: "Writing standard for private workspace files: agent definitions, agent guide, runbook, charter, and workspace instructions."
---
# Private workspace writing standard

Private files follow the same register as peer-facing pages (`peer-writing.instructions.md`): precise, impersonal, and free of conversational language. Private files may name agents, models, handoff files, and `.github/`; agent files address the agent directly ("You ...").

## Register

- Imperative, direct sentences. One rule per bullet. No emojis, exclamations, or rhetorical questions.
- Use the terminology table in `copilot-instructions.md`.
- Headings use sentence case ("Fixed handoff files", not "Fixed Handoff Files").
- Paths are repository-relative and in backticks. Placeholders use angle brackets: `<run_id>`, `<topic>`.

## Agent file structure

Every `.github/agents/*.agent.md` uses this front matter and section order. Optional sections are marked.

```markdown
---
name: <Role name>
description: "Use when <comma-separated triggers>."
model: "<model label>"
tools: [<tools>]
user-invocable: true
---
# <Role name>

<One paragraph: discipline and seniority, what the role owns, and what it does not own.>

## Inputs
| Input | Location | Format |

## Outputs
| Output | Location | Format |

## Procedure            (optional; numbered steps)

## Responsibilities

## Professional standard   (role-specific senior practice)

## Constraints

## Handoff
Handoff file path and the role-specific fields beyond the common fields in `AGENT_GUIDE.md`.
```

- `Inputs` and `Outputs` list every file the role reads or writes, with location and format. A role must not write anywhere not listed in its `Outputs`.
- Each output location has exactly one owning role, except handoff files.
- Roles with the `execute` tool run Python only as `conda run -n {{conda_env}} python ...`.
- Roles without the `edit` tool return their handoff in chat; the Coordinator writes the file.
- A rule that applies to all agents belongs in `copilot-instructions.md` or `AGENT_GUIDE.md`, not in each agent file.
- Record every change to an agent file in `.github/agents/CHANGELOG.md` with its evidence and approval.
