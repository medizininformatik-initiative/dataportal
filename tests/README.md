# Integration tests

The tests in this directory run against a real data node and data portal, started from the
compose files of this repository with the component versions they pin. They check that the
pinned versions work together. Unit tests of the components live in the component repositories.

Update this file when you add, move or remove a test file, or when a defect is fixed.

## CI jobs

All jobs are defined in [.github/workflows/ci.yml](../.github/workflows/ci.yml). They run on
every pull request and on pushes to `main`, `develop` and release tags.

| Job | Stack | Command | Duration |
| --- | --- | --- | --- |
| `lint` | none | shellcheck of all shell scripts outside `.github/scripts` | < 1 min |
| `integration-portal` | data node profile `core` + data portal + portal test user | `pytest tests/api tests/ui -m smoke` | about 34 min, of which about 10 min load the ontology into Elasticsearch |
| `test-data-node-e2e` | data node profile `full` | `pytest tests/node tests/pipeline --ignore=tests/pipeline/test_dup_pipeline_profiles.py` | about 8 min |
| `test-dup-pipeline-profiles` | data node profile `pipeline` | `pytest tests/pipeline/test_dup_pipeline_profiles.py` | about 16 min |

Every job with a stack loads the MII test data first (`get-mii-testdata.sh`,
`data-node/upload-testdata.sh`). The node profiles are defined in
[.github/scripts/setup-data-node.sh](../.github/scripts/setup-data-node.sh):

- `full`: every data node service.
- `core`: FHIR server with its Keycloak, reverse proxy and TORCH. Feasibility runs over CQL, so flare is not needed.
- `pipeline`: FHIR server, TORCH, DIMP and fhir-flattener. The DUP profile runs need the memory of a runner of their own.

All tests in `tests/api` and `tests/ui` carry the `smoke` marker. The `full` marker in
`pytest.ini` is not used yet.

## Components by job

The cells name the test files that exercise a component. Paths are relative to `tests/`.

| Component | `integration-portal` | `test-data-node-e2e` | `test-dup-pipeline-profiles` |
| --- | --- | --- | --- |
| dataportal-ui | all of `ui/` except `test_blaze_frontend.py` | | |
| dataportal-backend | `api/test_portal_smoke.py`, `test_backend_contracts.py`, `test_backend_variants.py`, `test_feasibility_golden.py`, `test_ontology.py`, all of `ui/` | | |
| Ontology (Elasticsearch, value sets, criteria sets) | `api/test_ontology.py`, `test_backend_contracts.py`, `test_feasibility_golden.py`, `ui/test_cohort_search_filters.py`, `ui/test_data_selection.py` | | `pipeline/test_dup_pipeline_profiles.py` (generated data for every data selection profile) |
| Portal Keycloak | `api/test_portal_smoke.py`, `ui/test_login.py` | | |
| availability-updater | `api/test_availability_updater.py` | | |
| Blaze FHIR server | `api/test_feasibility_golden.py` (CQL), `api/test_availability_updater.py` | `node/test_basic_queries.py`, `pipeline/test_blaze_auth.py`, `pipeline/test_node_services.py` | as data source |
| Blaze frontend + node Keycloak | `ui/test_blaze_frontend.py` | | |
| Terminology server | | `pipeline/test_node_services.py` (healthcheck, package range) | |
| fhir-data-evaluator | `api/test_availability_updater.py` | `pipeline/test_node_services.py` | |
| TORCH | `api/test_availability_updater.py` (indirect) | `pipeline/test_torch_api.py`, `test_torch_consent.py`, `test_torch_extraction.py`, `test_aether_cli.py`, `test_dup_pipeline.py` | `pipeline/test_dup_pipeline_profiles.py` |
| fhir-pseudonymizer (DIMP) | | `pipeline/test_dimp_service.py`, `test_dimp_required_references.py`, `test_dup_pipeline.py`, `test_torch_extraction.py`, `test_aether_cli.py` | `pipeline/test_dup_pipeline_profiles.py` |
| fhir-flattener | | `pipeline/test_flattener.py`, `test_aether_cli.py` | `pipeline/test_dup_pipeline_profiles.py` |
| mii-fhir-validator | | `pipeline/test_node_services.py`, `test_torch_extraction.py` | |
| aether | | `pipeline/test_aether_cli.py`, `test_dup_pipeline.py` | `pipeline/test_dup_pipeline_profiles.py` |
| flare | not tested, to be deprecated | | |

## Test files

The plan column refers to the rows of the dataportal 7.0.0 release test plan (for example
`ON-9`, `TO-2`). The defect column refers to the [known defects](#known-defects) below.

### `integration-portal`

| File | Checks | Plan rows | Defects |
| --- | --- | --- | --- |
| `api/test_portal_smoke.py` | Backend is up and accepts tokens of the portal Keycloak | | |
| `api/test_feasibility_golden.py` | Feasibility counts on the MII test data through backend, CQL and Blaze, compared with `golden/feasibility.json` and an independent FHIR search | B3 | |
| `api/test_ontology.py` | Every UI profile filter offers concepts or criteria, every UI profile runs over CQL, every data selection profile resolves, criteria sets stay in their context, umlaut search, English display of ICD-10-GM and SNOMED CT, no non-DomainResource profiles | B1, B2, B4, ON-2, ON-5, ON-8, ON-9, ON-10, ON-13 | D5, D7, D9, D24 |
| `api/test_backend_contracts.py` | Profile search, bulk search, Elasticsearch logging, ontology version, CRTDL upgrade, CSV export of a CRTDL, error code of an invalid CCDL | BE-3, BE-4, BE-8, BE-10, BE-11, UI-11 | D2, D3, D4 |
| `api/test_backend_variants.py` | Backend variants in their own container: query result expiry, soft quota 429, dispatch error with an unreachable FHIR server | BE-5, BE-7, UI-18 | D21 |
| `api/test_availability_updater.py` | Updater reads FDE reports, updates and lowers counts, data selection availability | AU-3, AU-4, ON-12 | D19 |
| `ui/test_login.py` | Sign-in and sign-out through the portal Keycloak, no browser errors | C1 | D1 |
| `ui/test_feasibility_query.py` | Build and run a query in the browser, count equals the golden value | C4, UI-1, UI-5 | |
| `ui/test_criterion_filters.py` | Attribute, value and exclusion filters in the criterion editor, count equals the golden value | C3, UI-2 | |
| `ui/test_cohort_search_filters.py` | Filter dropdowns of the criteria search: order, search field, dependent options | C2, UI-3 | |
| `ui/test_cohort_editor.py` | Time period for all criteria, codes in the reference selection | UI-12 | |
| `ui/test_bulk_search.py` | Bulk search keeps order, reports duplicates and unknown codes | UI-17 | |
| `ui/test_saved_queries.py` | Save, reload, run and delete a data definition | C5 | |
| `ui/test_crtdl_roundtrip.py` | Download, upload and run a CRTDL, upgrade of an ontology 4 CRTDL | C6, UI-11, UI-19 | |
| `ui/test_data_selection.py` | Feature search, "only if referenced", warning tiles, numbered and reordered features, blocked export | C7, C8, UI-4, UI-6, UI-8, UI-9, UI-10 | |
| `ui/test_ui_details.py` | Upload replaces the query, English labels, profile details, a code in two terminologies | UI-7, UI-13, UI-14 | |
| `ui/test_rate_limit.py` | UI shows the soft quota error of the backend | UI-18 | D23 |
| `ui/test_blaze_frontend.py` | Blaze frontend sign-in through the node Keycloak behind the reverse proxy | BL-2 | |

### `test-data-node-e2e`

| File | Checks | Plan rows | Defects |
| --- | --- | --- | --- |
| `node/test_basic_queries.py` | FHIR search counts on the MII test data (Consent, Condition) | | |
| `pipeline/test_blaze_auth.py` | Blaze with `OPENID_PROVIDER_ISSUER` and `OPENID_AUDIENCE`, each in its own container | BL-3 | |
| `pipeline/test_node_services.py` | Blaze healthchecks with wget, FDE MeasureReport and paging, validator IGs, terminology package range, R5 extensions | BL-1, BL-4, BL-5, FD-1, VA-1, VA-2, VA-3 | D10, D11, D12 |
| `pipeline/test_torch_api.py` | Task API (pause, resume, cancel), Patient.identifier, cohort size, metrics, `$evaluate-cohort`, `$translate-cql`, 405, date filter | TO-1, TO-7, TO-8, TO-11, TO-12, TO-15, ON-7 | D20 |
| `pipeline/test_torch_consent.py` | Consent rules on crafted patients: required policies, encounter shift, permit and deny, order by date, masked references, consent switched off | TO-2 to TO-6, TO-10 | |
| `pipeline/test_torch_extraction.py` | Extracted MII test data validates, Medikation profiles, DIMP adds no validation errors, manifest links, paging | TO-9, TO-14, ON-11, PS-4, BL-4 | D13 |
| `pipeline/test_dimp_service.py` | DIMP called directly: decompression, remove method, request size limit, cryptoHash of references | PS-4, PS-5 | D14, D15 |
| `pipeline/test_dimp_required_references.py` | The example DUP DIMP config never empties a required Reference | | |
| `pipeline/test_flattener.py` | `ViewDefinition/$run`: RFC 4180 CSV, no data from one run in the next | FF-1, FF-2 | D16 |
| `pipeline/test_aether_cli.py` | aether CLI: flattening, start checks, auth, Ctrl+C and job control, status, local import, DIMP decimals and splitting, send, config overrides | ON-6, AE-3 to AE-5, AE-7 to AE-14 | D17 |
| `pipeline/test_dup_pipeline.py` | Example DUP pipeline run twice: each DIMP rule changes the output between an empty and the real config | | |

### `test-dup-pipeline-profiles`

| File | Checks | Plan rows | Defects |
| --- | --- | --- | --- |
| `pipeline/test_dup_pipeline_profiles.py` | One generated CRTDL per data selection profile of the pinned ontology through TORCH, DIMP and fhir-flattener, 4 in parallel, failed runs retried alone. Data and CRTDLs come from `pipeline/ontology_testdata.py` | | D26 |

## Known defects

A test for a confirmed defect is marked `xfail(strict=True)`, or its problems are listed in
[golden/known-issues.json](golden/known-issues.json). Both fail when the defect is fixed, so
the marker or entry has to be removed. Low priority defects are marked (low).

| Code | Component | Defect | Tracked in |
| --- | --- | --- | --- |
| D1 (low) | dataportal-ui | Sends `Authorization: Bearer null` to `/backend/.settings` before login | `ui/test_login.py` |
| D2 (low) | dataportal-backend | 500 instead of 400 for a criterion without its mandatory value filter | `api/test_backend_contracts.py` |
| D3 (low) | dataportal-backend | CRTDL upgrade drops `"attributes": []` and then rejects the upgraded CRTDL | `api/test_backend_contracts.py` |
| D4 | Ontology | Releases v5.2.1 and v5.2.2 stamp their indices as v5.2.0 | `api/test_backend_contracts.py` |
| D5 | Ontology | 8 value sets referenced by data selection code filters are missing | known issue `data-selection-code-filters` |
| D7 (low) | Ontology | Value filter of "TNM m symbol" references an empty criteria set | known issue `ui-profile-filters` |
| D9 | Ontology | 119 ICD-10-GM 2026 codes have no English or German display | known issue `english-display` |
| D10 | Data node | Terminology `package.json` range cannot reach the BOM the validator expects | `pipeline/test_node_services.py` |
| D11 | Data node | FDE `.env.default` points at the validator port instead of Blaze | `pipeline/test_node_services.py` |
| D12 (low) | fhir-data-evaluator | MeasureReport lacks the R4 mandatory elements | `pipeline/test_node_services.py` |
| D13 | TORCH | Extracted ObservationLab resources fail their profile | known issue `torch-output-validation` |
| D14 | fhir-pseudonymizer | cryptoHash of references also hashes the data-absent-reason extension | `pipeline/test_dimp_service.py` |
| D15 | Data node | Example DUP bundle threshold (100 MB) is above the DIMP request limit (30 MB) | `pipeline/test_dimp_service.py` |
| D16 (low) | fhir-flattener | CSV without header row | `pipeline/test_flattener.py` |
| D17 | Data node | Example `services.send.url` ends in `/fhir`, aether sends to `/fhir/fhir` | `pipeline/test_aether_cli.py` |
| D19 | availability-updater | Nothing writes data selection availability | `api/test_availability_updater.py` |
| D20 | TORCH | `DELETE /fhir/Task/{id}` keeps the Task and the result files ([torch#1391](https://github.com/medizininformatik-initiative/torch/issues/1391)) | `pipeline/test_torch_api.py` |
| D21 | dataportal-backend | Dispatch error log does not name the cause | `api/test_backend_variants.py` |
| D23 | dataportal-ui | Ignores the 429 of the soft quota and waits without end | `ui/test_rate_limit.py` |
| D24 | Ontology | SNOMED CT 21371007 is selectable in context Procedure, but its query never finishes ([fhir-ontology-generator#570](https://github.com/medizininformatik-initiative/fhir-ontology-generator/issues/570)) | `api/test_ontology.py` |
| D26 | fhir-flattener | Exits with code 0 and no log under sustained load (non-strict xfail, aether retries hide it) | `pipeline/test_dup_pipeline_profiles.py` |

## Running locally

1. Start the stacks the job needs: `DATA_NODE_PROFILE=<profile> .github/scripts/setup-data-node.sh`,
   load the test data, and for `tests/api` and `tests/ui` also `.github/scripts/setup-data-portal.sh`
   and `.github/scripts/create-portal-test-user.sh`.
2. `pip install -r tests/requirements.txt` and `playwright install chromium`.
3. Run the job's pytest command from the repository root with `DATA_PORTAL_COMPOSE_PROJECT=test`.

Do not run two pytest processes against the same stack at once. Several tests start extra
containers with fixed names and ports next to the stack (TORCH, Blaze and backend variants,
a TORCH stand-in), and tests that change shared data (crafted patients, FDE reports) clean
up only after their module.

## Helpers

| File | Purpose |
| --- | --- |
| `helpers.py`, `conftest.py` | Shared helpers and fixtures, `known_issues` baseline check |
| `feasibility.py` | Feasibility queries built from the golden cases, plus the FHIR search oracle |
| `torch_client.py` | TORCH `$extract-data` client, FHIR server access, TORCH variant container |
| `backend_variant.py` | Second backend container with config overrides |
| `fde.py`, `availability.py` | Run fhir-data-evaluator and the availability updater as the data node does |
| `pipeline/torch_stub.py` | TORCH stand-in that never finishes, and a FHIR server that holds every search |
| `pipeline/ontology_testdata.py` | Generates CRTDLs and test data for every data selection profile |
| `ui/pages/` | Page actions for the Playwright tests |
| `golden/` | Golden feasibility counts and the known issues baseline |
