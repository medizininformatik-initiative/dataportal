# DUP Pipeline Test

Runs every CRTDL in a folder through aether with the pipeline from [example-dup-project](../example-dup-project) and checks whether each pipeline run succeeded.

## Prerequisites

1. The data node is running and test data is loaded into the FHIR server. The pipeline uses TORCH, fhir-pseudonymizer (DIMP) and fhir-flattener.
2. The vfps namespaces exist. Create them with [example-project-create-namespaces-vfps.sh](../example-dup-project/example-project-create-namespaces-vfps.sh).
3. `aether` is on the `PATH`.
4. Python 3.9 or newer is installed. The script needs only the standard library.

## Usage

```bash
./run-dup-pipeline-tests.py
```

| Option | Default | Description |
| --- | --- | --- |
| `--crtdl-dir` | `input-crtdls` | Folder with the CRTDL `*.json` files |
| `--example-dir` | `../example-dup-project` | Example DUP project. aether runs in this directory, so the relative paths in its config resolve. |
| `--pipeline` | `example-project-pipeline.yml` | Pipeline config file inside `--example-dir` |
| `--modes` | `as-is cohort-replaced` | Modes to run, e.g. `--modes as-is` |
| `--cohort` | `replacement-cohort.json` | Cohort definition for the `cohort-replaced` mode |
| `--results-dir` | `results` | Output folder |
| `--aether` | `aether` | aether binary |
| `--timeout` | `3600` | Timeout per run in seconds |
| `--parallel` | `4` | Number of aether runs at the same time. Use `1` if TORCH or fhir-flattener fail under load. |
| `--torch-poll-interval` | `1` | Seconds between TORCH status polls (minimum 1). Replaces `polling_interval_seconds` in the generated config with `polling_interval`. |

The script exits with 0 if all runs pass and with 1 otherwise.

## Test modes

By default each CRTDL runs in both modes. `--modes` selects a subset:

- `as-is`: the CRTDL is used unchanged.
- `cohort-replaced`: `cohortDefinition` is replaced with [replacement-cohort.json](replacement-cohort.json), which selects all female and male patients. This mode separates errors in the cohort definition from errors in the data extraction.

## Pass criteria

A run passes if all of these hold:

1. aether exits with code 0.
2. `state.json` reports the job status `completed`.
3. Every pipeline step has the status `completed`.
4. The flattening step wrote at least one CSV.

## Output

For each run, the script copies the pipeline config and changes only `jobs_dir`, so that the aether job ends up in the results folder. Nothing is written to `example-dup-project/jobs`.

```text
results/<timestamp>/
  summary.md                 table of all runs: result, step statuses, CSV row counts, error
  summary.json               same data, machine-readable
  <crtdl-name>/<mode>/
    crtdl.json               CRTDL that was submitted
    pipeline.yml             generated aether config
    aether.log               aether stdout and stderr
    jobs/<job-id>/           aether job directory
    job -> jobs/<job-id>     symlink to the job directory
```

The job directory contains the pipeline output files:

- `import/`: FHIR NDJSON extracted by TORCH
- `dimp/`: pseudonymized NDJSON
- `csv/`: flattened CSV files, one per attribute group
- `viewdefinitions/`: ViewDefinitions used for flattening
- `enriched-crtdl.json`: the CRTDL after aether's preprocessing (enrichment), as sent to TORCH
- `state.json`, `job.log`: job state and log

`results/` is git-ignored.

## Example input

The CRTDLs in [input-crtdls](input-crtdls) have these expected results:

| CRTDL | Change | Expected result |
| --- | --- | --- |
| `example-project-crtdl.json` | none | Both modes pass. Its cohort is the same as `replacement-cohort.json`. |
| `example-project-crtdl-broken-cohort.json` | gender code `female` → `test` | Both modes pass. The concepts are OR-combined, so `as-is` returns only the male patients. |
| `example-project-crtdl-broken-extraction.json` | broken cohort and unknown profile `Diagnose-broken` | Both modes fail, because TORCH rejects the profile with HTTP 400. |

## Ontology tests

[generate-ontology-tests.py](generate-ontology-tests.py) generates test data and CRTDLs that cover every DSE profile (feature) and every field (attribute) of a [fhir-ontology-generator](https://github.com/medizininformatik-initiative/fhir-ontology-generator) release.

```bash
./generate-ontology-tests.py --release v5.2.1 --upload
./run-dup-pipeline-tests.py --crtdl-dir ontology-tests/crtdls
```

| Option | Default | Description |
| --- | --- | --- |
| `--release` | `v5.2.1` | Release tag. The script downloads `backend.zip` and `dse_structures.zip` from the release. |
| `--cache-dir` | `.cache` | Download cache. It also holds the FHIR R4 core package. |
| `--out-dir` | `ontology-tests` | Output folder |
| `--cohort` | `replacement-cohort.json` | Cohort of every CRTDL |
| `--upload` | off | POST the test data bundle to `--fhir-url` |
| `--fhir-url` | `https://fhir.localhost:444/fhir` | FHIR server of the data node |

Output:

- `crtdls/<module>--<profile>.json`: one CRTDL per DSE profile. The cohort selects all female and male patients. The profile's attribute group selects every field id of the DSE profile tree, including nested slices, and every reference field. Each reference field links to one of its DSE target profiles. Linked groups and the Patient group select the first top-level field of their own DSE profile, because aether requires at least one attribute per group. CRTDLs contain only attributes of the DSE profiles.
- `testdata/ontology-testdata.json`: transaction bundle with resources for every profile. Ids start with `ot-`, so a new upload overwrites the previous one. Each profile gets one resource per type of its widest choice element, so every `[x]` type occurs.
- `coverage.md`, `coverage.json`: DSE fields and reference fields that no generated resource fills, and the profile defects the generator found.

The test data is structurally valid: it sets `meta.profile`, fills every element allowed by the snapshot, and applies fixed and pattern values, slice discriminators and extension URLs. It takes codes from the core FHIR value sets. Codes from MII value sets are placeholders, because the release does not contain them.

Constraints from TORCH and the example pipeline:

- All CRTDLs use `PatientPseudonymisiert` as Patient group, because the pipeline's CRTDL preprocessing adds this group and TORCH allows only one Patient group. For the same reason the CRTDLs of the profiles `Patient` and `ISiKPatient` always fail.
- TORCH supports only DomainResource types. The CRTDLs of `Bundle` and `Binary` profiles fail.
- All generated resources except patients belong to one patient, because TORCH resolves references within a patient compartment.
- `subject` and `patient` always reference the patient, also where the DSE offers only Device profiles as targets. TORCH links these fields to the Patient group.
