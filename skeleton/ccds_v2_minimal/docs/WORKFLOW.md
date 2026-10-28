# Analysis workflow

The workflow is a sequence of explicit stages. Each stage consumes versioned inputs and produces a record of what it read, ran, and wrote; downstream work starts only after its acceptance checks pass.

| Stage | Input | Record and acceptance |
| --- | --- | --- |
| 0. Extraction (optional) | Restricted sources | Raw inputs in `data/raw/` with provenance; requires access to the sources |
| 1. Input intake | Raw inputs | Input manifest with file counts, sizes, schemas, and SHA-256 hashes |
| 2. Research | Question, input manifest, earlier results | Hypotheses, discriminating tests, results with uncertainty, proposed decision; design changes approved before implementation |
| 3. Design | Approved research, current data | Data contracts and design records with options considered |
| 4. Pipeline | Input manifest, frozen config | Processed data and run outputs with row counts and hashes; tests pass |
| 5. Modeling | Processed data, frozen split and seeds | Models and evaluation with uncertainty against a baseline |
| 6. Review | Run outputs, config, code | Independent review of assumptions, evaluation, uncertainty, and discrepancies |
| 7. Figures | Reviewed outputs | Figures produced by code, with captions and sources |
| 8. Reports | Reviewed outputs and figures | Linked report with verified claims and limitations |
| 9. Release | All accepted stages | Reproduction record |

## Run identifiers and folders

Each run has an identifier `YYYYMMDD_<slug>` and one folder `runs/<run_id>/` containing the frozen config, the input manifest, and all outputs. Earlier runs are never overwritten; superseded runs are kept and labelled as historical.

## Input manifest

```powershell
conda run -n {{conda_env}} python -m {{module_name}}.input_manifest --sha256 --write-manifest runs/<run_id>/input_manifest.json
conda run -n {{conda_env}} python -m {{module_name}}.input_manifest --compare data/input_manifest.json runs/<run_id>/input_manifest.json
```

Only a matching SHA-256 shows that two files are identical; equal size and name do not.

## Reproduction record

Each released run contains:

- run ID and UTC timestamp;
- source revision and package versions;
- input manifest path and hashes;
- configuration path;
- exact commands;
- output file paths, row counts, and hashes;
- validation and test results, and limitations.
