# Changelog

All notable changes to this project will be documented in this file.

## Component specific changes

Please refer to the respective repositories for a more in depth changelog of single components:

|Component|Link|
|--|--|
|Dataportal UI|<https://github.com/medizininformatik-initiative/dataportal-ui>|
|Dataportal Backend|<https://github.com/medizininformatik-initiative/dataportal-backend>|
|Dataportal Availability Updater|<https://github.com/medizininformatik-initiative/dataportal-availibility-updater>|
|Ontology Generation|<https://github.com/medizininformatik-initiative/fhir-ontology-generator>|
|sq2cql|<https://github.com/medizininformatik-initiative/sq2cql>|
|DSF Feasibility Process|<https://github.com/medizininformatik-initiative/mii-process-feasibility>|
|FLARE|<https://github.com/medizininformatik-initiative/flare>|
|Fhir Data Evaluator|<https://github.com/medizininformatik-initiative/fhir-data-evaluator>|
|Blaze FHIR server|<https://github.com/samply/blaze>|
|aether|<https://github.com/medizininformatik-initiative/aether>|
|TORCH|<https://github.com/medizininformatik-initiative/torch>|
|Blaze FHIR terminology server|<https://github.com/samply/blaze>|
|mii-fhir-validator|<https://github.com/medizininformatik-initiative/mii-fhir-validator>|
|fhir-flattener|<https://github.com/medizininformatik-initiative/fhir-flattener>|
|fhir-pseudonymizer|<https://github.com/miracum/fhir-pseudonymizer>|


## [7.0.0] - 2026-11-20

### Overview

This release makes the data use project (DUP) pipeline of the `data-node` production ready. TORCH and aether reached their first stable versions, the DIMP step supports per-project pseudonymisation, and the data selection uses the same search as the cohort selection. No services were added or removed.

Changes in this repository:

- Example DUP project with per-project dynamic pseudonymisation - [see](https://github.com/medizininformatik-initiative/dataportal/tree/main/data-node/example-dup-project)
- DIMP DUP configs mask required references with a data-absent-reason instead of pruning them, keep the re-pseudonymized patient and encounter identifiers and redact all other identifiers
- Consent documentation and an example consent CRTDL - [see](https://medizininformatik-initiative.github.io/dataportal/data-node/consent.html)
- Combined transfer load script for the send step, test data switched to the MII test data, data-portal env defaults use the context path setup (backend under `/backend`)
- Automated integration tests in CI - [see](https://github.com/medizininformatik-initiative/dataportal/tree/main/tests)
  - data-portal: backend API contracts, ontology checks, feasibility counts against golden values, availability-updater and browser tests of the UI
  - data-node: TORCH API, extraction and consent, aether CLI, DIMP, fhir-flattener, Blaze auth and the full DUP pipeline for every DSE profile
- Fixed the default `AVAILABILITY_REPORT_SERVER_BASE_URL` of the availability-updater (`fhir-sever` → `fhir-server`)
- Fixed the Keycloak database healthchecks of the data-portal and the data-node, which ran `pg_isready` with an empty user and database
- Fixed the flare certs mount, which was mounted read-write instead of read-only
- dataportal-backend 9.6.0: Listing data queries no longer fails with 500 for old entries that store a bare CCDL. The profile search with pinned profiles allocates about 1 MB instead of 32 MB per request. The backend now starts with a heap of about 1 GB. The tag v7.0.0 was moved on 2026-11-20 to include this fix. If you checked out v7.0.0 before, run `git fetch --tags --force` and check out v7.0.0 again

### Breaking changes

- postgres: The dataportal-backend database (`dataportal-postgres`), the data-portal keycloak database (`auth-db`) and the data-node keycloak database (`fhir-server-keycloak-db`) are upgraded from Postgres 17 to 18. Postgres 18 cannot start on Postgres 17 data, and the volume mount moved from `/var/lib/postgresql/data` to `/var/lib/postgresql`. Existing installations have to migrate their data. The commands below run from the repository root with the default compose project `dataportal` and the default database users.
  1. Before updating, dump each database with the old version running:
     - backend: `docker compose -p dataportal -f data-portal/backend/docker-compose.yml exec dataportal-postgres pg_dumpall -U dataportaluser > backend-dump.sql`
     - data-portal keycloak: `docker compose -p dataportal -f data-portal/keycloak/docker-compose.yml exec auth-db pg_dumpall -U keycloakdbuser > keycloak-dump.sql`
     - data-node keycloak: `docker compose -p dataportal -f data-node/fhir-server/keycloak.docker-compose.yml exec fhir-server-keycloak-db pg_dumpall -U keycloakdbuser > node-keycloak-dump.sql`
  2. Stop the stacks and remove the old volumes (`dataportal-postgres-data`, `dataportal_dataportal-auth-db`, `dataportal_fhir-server-keycloak-db`).
  3. Update the repository and start only the databases, for example `docker compose -p dataportal -f data-portal/keycloak/docker-compose.yml up -d auth-db`. Do not start Keycloak or the backend yet. They would create a new schema in the empty database, and the restore would then fail.
  4. Restore each dump:
     - backend: `docker compose -p dataportal -f data-portal/backend/docker-compose.yml exec -T dataportal-postgres psql -U dataportaluser -d postgres < backend-dump.sql`
     - data-portal keycloak: `docker compose -p dataportal -f data-portal/keycloak/docker-compose.yml exec -T auth-db psql -U keycloakdbuser -d postgres < keycloak-dump.sql`
     - data-node keycloak: `docker compose -p dataportal -f data-node/fhir-server/keycloak.docker-compose.yml exec -T fhir-server-keycloak-db psql -U keycloakdbuser -d postgres < node-keycloak-dump.sql`
     
     The errors `role ... already exists` and `database ... already exists` are expected.
  5. Start the stacks as usual.
- ontology: Ontology 5.x changes the Elasticsearch artifact. Reinstall the index once with `DATAPORTAL_ES_INIT_FORCE_REINSTALL="true"`.
- TORCH: Consent results differ from 6.0.0 - [see](https://medizininformatik-initiative.github.io/torch/implementation/consent.html)
  - Only `.8` and `.6` are evaluated and both must be in the CRTDL. Combined consent keys (e.g. `yes-yes-no-yes`) are no longer supported.
  - The consent start moves only to the start of an inpatient stay that began at most `TORCH_ENCOUNTER_SHIFT_MAX_DAYS` (default 7) days before.
  - `Patient.identifier` is no longer a standard attribute. Add it to the CRTDL if you need it, e.g. for re-pseudonymisation.
- fhir-pseudonymizer v3: Keys must be at least 32 bytes (`openssl rand -hex 32`). URL-like values that contain `~` or `-` are hashed differently, so such pseudonyms in 6.x extractions cannot be linked to 7.0.0 extractions.
- aether:
  - Call it as `aether pipeline start <aether.yaml> <crtdl.json>`. The `--config` flag is gone.
  - The DIMP output directory is now `dimp` (was `pseudonymized`).
  - Service URLs are server roots without `/fhir`.
  - `services.dimp.experimental_v3` is replaced by `services.dimp.anonymization_config`.
  - The first Ctrl+C asks for a confirmation. Scripts should send SIGTERM or use `aether job stop`.
- Blaze 1.13.0:
  - The image no longer contains `curl`, so healthchecks must use `wget`.
  - The frontend ignores `ORIGIN` and uses `HOST_HEADER` and `PROTOCOL_HEADER`. Users have to sign in again, and the reverse proxy must accept request headers of about 6 KB.
- mii-fhir-validator: Copy the new `IG_PARAMS` from `.env.default` into your `.env` and update the terminology in the local Blaze - [see](https://github.com/medizininformatik-initiative/mii-fhir-validator/releases/tag/v0.0.1-alpha.9)
- FLARE: Unsupported FHIR search parameters now fail a query instead of being ignored (`FLARE_FHIR_STRICT_HANDLING`, default `true`).
- dataportal-backend: The REST API moved to `/api/v6`. External API clients have to update their paths.
- TORCH 1.1.0: Compartment resources without a patient reference are excluded as `PATIENT_NOT_FOUND`, resources linked to several patients as `MULTIPLE_PATIENTS`. `job-summary.json` reports both counts.
- vfps: The vfps database is upgraded from Postgres 17.5 to 18.7. It has no named volume, so the updated container starts with an empty database and existing pseudonyms are lost. If you need them, dump the database before updating with `docker compose -p dataportal -f data-node/fhir-pseudonymizer/docker-compose.vfps.yml exec postgresql pg_dumpall -U postgres > vfps-dump.sql`. After the update start only the database with `docker compose -p dataportal -f data-node/fhir-pseudonymizer/docker-compose.vfps.yml up -d postgresql`, restore with `docker compose -p dataportal -f data-node/fhir-pseudonymizer/docker-compose.vfps.yml exec -T postgresql psql -U postgres -d postgres < vfps-dump.sql` and then start the data node.

### Security

- Java4Shell (CVE-2026-114938): All JVM services run with `-XX:-UseBASE64Intrinsics`. Elasticsearch sets it in `ES_JAVA_OPTS`, Keycloak in `JAVA_OPTS_APPEND`, the data-node services (Blaze, flare, TORCH, FDE, fhir-flattener, mii-fhir-validator) in `JDK_JAVA_OPTIONS`. The dataportal-backend image sets the flag itself. If you override these variables in your own setup, add the flag there.
- nginx HTTP/2 (CVE-2026-123633, CVE-2026-123007): The data-portal proxy, the data-node rev-proxy and torch-nginx use nginx 1.31.9, which fixes both vulnerabilities. The image is now pulled from `ghcr.io/nginx/nginx-unprivileged`, because Docker Hub does not publish 1.31.9 yet. If your site restricts container registries, allow `ghcr.io`. The tag v7.0.0 was first published on 2026-11-18 with nginx 1.31.7 and HTTP/2 disabled, and was moved on 2026-11-19 to this fix. If you checked out v7.0.0 before, run `git fetch --tags --force` and check out v7.0.0 again - [#226](https://github.com/medizininformatik-initiative/dataportal/issues/226)

### Ontology

This release is based on ontology version [v5.2.2](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v5.2.2) (was [v4.0.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v4.0.0)).

- New modules: Onkologie and MolGen 2026
- New attributes: interpretation for laboratory values, status for encounters
- Flattening lookup for aether (`flattening.zip`) is now part of the ontology release
- New Elasticsearch index for profile details, with German umlaut handling

### Updates since last Major

The versions of all components per release are listed in the [compatibility matrix](https://medizininformatik-initiative.github.io/dataportal/compatibility-matrix.html).

**Data Portal**

|Component|From|To|
|--|--|--|
|dataportal-ui|[v6.8.0](https://github.com/medizininformatik-initiative/dataportal-ui/releases/tag/v6.8.0)|[v7.3.4](https://github.com/medizininformatik-initiative/dataportal-ui/releases/tag/v7.3.4)|
|dataportal-backend|[v8.6.0](https://github.com/medizininformatik-initiative/dataportal-backend/releases/tag/v8.6.0)|[v9.6.0](https://github.com/medizininformatik-initiative/dataportal-backend/releases/tag/v9.6.0)|
|availability-updater|[v0.3.0](https://github.com/medizininformatik-initiative/dataportal-availibility-updater/releases/tag/v0.3.0)|[v0.4.2](https://github.com/medizininformatik-initiative/dataportal-availibility-updater/releases/tag/v0.4.2)|
|dataportal-es-init|2.0.0|3.1.0|
|Elasticsearch|9.2.4|9.5.6|
|Keycloak|26.3.1|26.8.2|
|Postgres (backend and Keycloak)|17|18.7|
|nginx (proxy)|1.27|1.31.9|

**Data Node**

|Component|From|To|
|--|--|--|
|FHIR Server - Blaze|[v1.6.2](https://github.com/samply/blaze/releases/tag/v1.6.2)|[v1.13.0](https://github.com/samply/blaze/releases/tag/v1.13.0)|
|terminology server (blaze)|[v1.6.2](https://github.com/samply/blaze/releases/tag/v1.6.2)|[v1.13.0](https://github.com/samply/blaze/releases/tag/v1.13.0)|
|TORCH|[v1.0.0-alpha.18](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.18)|[v1.1.0](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.1.0)|
|FLARE|[v2.7.0](https://github.com/medizininformatik-initiative/flare/releases/tag/v2.7.0)|[v2.9.0](https://github.com/medizininformatik-initiative/flare/releases/tag/v2.9.0)|
|FDE|[v1.3.3](https://github.com/medizininformatik-initiative/fhir-data-evaluator/releases/tag/v1.3.3)|[v1.3.3](https://github.com/medizininformatik-initiative/fhir-data-evaluator/releases/tag/v1.3.3)|
|aether|[v0.6.0](https://github.com/medizininformatik-initiative/aether/releases/tag/v0.6.0)|[v1.6.0](https://github.com/medizininformatik-initiative/aether/releases/tag/v1.6.0)|
|fhir-pseudonymizer|[v2.23.0](https://github.com/miracum/fhir-pseudonymizer/releases/tag/v2.23.0)|[v3.1.2](https://github.com/miracum/fhir-pseudonymizer/releases/tag/v3.1.2)|
|vfps|[v1.3.6](https://github.com/miracum/vfps/releases/tag/v1.3.6)|[v1.28.0](https://github.com/miracum/vfps/releases/tag/v1.28.0)|
|mii-fhir-validator|[0.0.1-alpha.5](https://github.com/medizininformatik-initiative/mii-fhir-validator/releases/tag/v0.0.1-alpha.5)|[0.0.1-alpha.9](https://github.com/medizininformatik-initiative/mii-fhir-validator/releases/tag/v0.0.1-alpha.9)|
|Postgres (vfps)|17.5|18.7|
|Keycloak (FHIR server auth)|26.3.1|26.8.2|
|Postgres (Keycloak)|17|18.7|
|nginx (rev-proxy)|1.27|1.31.9|
|fhir-flattener|[0.1.0-alpha.7](https://github.com/medizininformatik-initiative/fhir-flattener/releases/tag/v0.1.0-alpha.7)|[0.1.0-alpha.10](https://github.com/medizininformatik-initiative/fhir-flattener/releases/tag/v0.1.0-alpha.10)|

The full list of changes is in the release notes of each component, linked in the table.

### Highlights

- **dataportal-ui:** Angular 19. Elasticsearch-based search replaces the tree in the data selection. Criteria are edited on their own page. Shortcuts lead to missing filters and unlinked references. CSV download of the data selection. Collapsible criteria tiles, layout for lower screen resolutions, more robust result polling and `linux/arm64` images.
- **dataportal-backend:** Spring Boot 4. Feature search with field descriptions and pinned profiles. sq2cql replaced by cctb-cql. The CRTDL upgrade removes filters the ontology no longer supports. Startup check that the Elasticsearch index matches the ontology version (`ELASTIC_SEARCH_ONTOLOGY_VERSION_CHECK_MODE`, default `warn`).
- **availability-updater:** Reads the ontology 5.x layout and uses less memory. OAuth2 and basic auth for the ontology download.
- **TORCH:** First stable release. Task API to submit, pause, cancel and delete jobs and to follow their progress. Consent calculation follows the MII consent specification and reports conflicts. Extraction-exclusion list and Prometheus metrics. Masks required elements with data-absent-reason stubs and reports resources that still violate required cardinality as job issues.
- **aether:** First stable release. Checks the CRTDL, the flattening lookup and the connected services before a job starts. New commands `aether job stop` and `aether send`. Re-attaches to running TORCH extractions.
- **fhir-pseudonymizer:** Per-project anonymization config on `$de-identify` and per-context key derivation.
- **mii-fhir-validator:** 2026 MII KDS packages, HL7 validator 6.9.11.
- **Blaze:** Faster small transactions and JSON parsing. Optional `iss` and `aud` checks for JWTs. Security fixes.
- **fhir-flattener:** RFC 4180 CSV, lower memory use.
- **FLARE:** Strict handling of search parameters. **FDE:** no changes.


## [6.3.0] - 2026-06-22

### Updates since last version

For updates to the components since the last version see the [compatibility matrix ](https://medizininformatik-initiative.github.io/dataportal/compatibility-matrix.html)
For detailed overview of releases see the individual components

### Breaking changes

- fhir-pseudonymizer: Updated documentation for pseudonymization inlcuding DUP specific crypto hashes and identifier


### Major New Features

- flattening: Support more fields to flattening - new flatteningLookup.json - see ontology 4.2.0


### Ontology

This release is based on ontology version [v4.2.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v4.2.0)


## [6.2.0] - 2026-06-18

### Updates since last version

For updates to the components since the last version see the [compatibility matrix ](https://medizininformatik-initiative.github.io/dataportal/compatibility-matrix.html)
For detailed overview of releases see the individual components

### Breaking changes

- aether: aether.yaml is now a required first positional argument — The --config flag is gone;
- aehter: DIMP step output directory renamed pseudonymized → dimp — Downstream steps and external tooling that read the pseudonymized output must use the new

### Fixes

- Added additional documentation
- Added Anonymization__CryptoHashKey env var to pseudonymizer
- TORCH: No longer extends encounter when consent is signed on the encounter end date - for info on consent in torch [see](https://medizininformatik-initiative.github.io/torch/implementation/consent.html)

### Major New Features
- aether
  - Copy effective CRTDL into job dir
  - Service urls now standardized to service root - aether adds /fhir to the url.
- TORCH
  - Provide extraction-exclusion list in TORCH output 

### Ontology

This release is based on ontology version [v4.1.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v4.1.0)


## [6.1.0] - 2026-05-21

### Updates since last version

For updates to the components since the last version see the [compatibility matrix ](https://medizininformatik-initiative.github.io/dataportal/compatibility-matrix.html)
For detailed overview of releases see the individual components

### Breaking changes

- aether: Service urls now standardized to service root - aether adds /fhir to the url
- aether: Removed flatteningLookup.json as it is now part of the ontology generation files - [see documentation](https://medizininformatik-initiative.github.io/dataportal/data-node/aether.html#setting-up-aether)
- TORCH: Updated Consent Calculation - [see](https://github.com/medizininformatik-initiative/torch/issues/851)

### Fixes

- Added additional documentation
- Fixed dimp_dup_base.yml zip code generalization

### Major New Features

- UI
  - Add filtering of filter options for criteria search
  - Move criterion editing to its own page
- Backend
  - Add filtering of filter options for criteria search
- aether
  - Copy effective CRTDL into job dir
  - Service urls now standardized to service root - aether adds /fhir to the url.
- TORCH
  - Updated Consent Calculation to support Consent for central analysis - [see](https://medizininformatik-initiative.github.io/torch/implementation/consent.html)
  - Implemented job handling and Task API

### Ontology

This release is based on ontology version [v4.1.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v4.1.0)

- New module oncology added.
- Added `flattening.zip` (fhir flattening viewdefintion lookup) as part of the ontology assets.


## [6.0.0] - 2026-03-31


### Overview 

**Feasibility Portal**    -> **Data Portal**
**Feasibility Triangle**  -> **Data Node**

Since the last major the repository has been refactored to reflect the additional functionality of the dataportal.
It was devided into a `data-portal` and a `data-node` part.

Additionally, the `data-node`, which replaced the `feasibility-triangle` now includes additional services, supporting the full data use project (DUP) pipeline at the node site.

In this context we have also updated and improved the documentation.

The DUP Pipeline includes the services described [here](https://medizininformatik-initiative.github.io/dataportal/data-node/overview.html#data-node-services).

The following services or components are new:

- DUP Pipeline Coordinator (aether)
- FHIR Terminology Server (Blaze)
- De-Identification, Minimization, Pseudonymization DIMP (fhir-pseudonymizer)
- FHIR Validation (fhir-validator)
- FHIR Flattening (fhir-flattener)


### Ontology

Current: **[v4.0.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v4.0.0)**
Changed since laster Major Release FROM [v3.8.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.8.0) To [v4.0.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v4.0.0)

#### Major Ontology Updates

* Upgrade all resources to use CDS version 2025 by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/445
* Remove primitively-typed elements from DSE profile details tree by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/303
* Create scorecard.yml by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/392
* 320 create broad availability measure by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/329
* Fix intermediate nodes missing in profile tree and add ordering by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/395
* Address backend issues 344, 357, and 358 by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/398
* Add ref-based targeting to GitHub FHIR package manager and fix unnecessary inflation by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/407
* Implement configurable field handling in DSE via config file by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/412
* Add value set display values to terminology display mapping file by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/413
* Add missing field exclusion if occurence is 0 for profile details by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/417
* Implement category based procedure criterion class for FDPG project by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/418
* Include admission identifier of MII CDS Encounter profile by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/439
* Rework field config and change identifier handling by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/443
* Allow multiple value set references in UI profile attributes by @Frontman50 in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/314
* Ensure backbone references are selectable by @Frontman50 in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/363
* Adapt generator to new MII CDS ICU module version by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/361
* Restrict allowed units of age criterion class by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/368


### Updates since last Major

**Data Portal**

|Component|From|To|
|--|--|--|
|dataportal-ui|[v6.3.3](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.3.3)|[v6.8.0](https://github.com/medizininformatik-initiative/dataportal-ui/releases/tag/v6.8.0)|
|dataportal-backend|[v7.3.0](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.3.0)|[v7.3.0](https://github.com/medizininformatik-initiative/dataportal-backend/releases/tag/v8.6.0)|
|Keycloak|quay.io/keycloak/keycloak:26.3.1|quay.io/keycloak/keycloak:26.3.1|
|availability-updater|-|[0.3.0](https://github.com/medizininformatik-initiative/dataportal-availibility-updater/releases/tag/v0.3.0)|

**Data Node**

|Component|From|To|
|--|--|--|
|FHIR Server - Blaze|[v1.0.4](https://github.com/samply/blaze/releases/tag/v1.0.4)|[v1.6.2](https://github.com/samply/blaze/releases/tag/v1.6.2)|
|TORCH|[1.0.0-alpha.6](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.6)|[1.0.0-alpha.18](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.18)|
|FLARE|[2.6.0](https://github.com/medizininformatik-initiative/flare/releases/tag/v2.6.0)|[2.7.0](https://github.com/medizininformatik-initiative/flare/releases/tag/v2.7.0)|
|FDE|[1.3.1](https://github.com/medizininformatik-initiative/fhir-data-evaluator/releases/tag/v1.3.1)|[1.3.3](https://github.com/medizininformatik-initiative/fhir-data-evaluator/releases/tag/v1.3.3)|
|aether|-|[0.6.0](https://github.com/medizininformatik-initiative/aether/releases/tag/v0.6.0)|
|fhir-pseudonymizer|-|[2.23.0](https://github.com/miracum/fhir-pseudonymizer/releases/tag/v2.23.0)|
|mii-fhir-validator|-|[0.0.1-alpha.5](https://github.com/medizininformatik-initiative/mii-fhir-validator/releases/tag/v0.0.1-alpha.5)|
|terminology server (blaze)|-|[1.6.2](https://github.com/samply/blaze/releases/tag/v1.6.2)|
|fhir-flattener|-|[0.1.0-alpha.7](https://github.com/medizininformatik-initiative/fhir-flattener/releases/tag/v0.1.0-alpha.7)|


### Major Changes since last Major

#### dataportal-ui

* Infinite scrolling – implemented for CodeableConcept search, Criteria search, and Reference search [#217](https://github.com/medizininformatik-initiative/feasibility-gui/issues/217)
* Support loading of query by id via url params [#416](https://github.com/medizininformatik-initiative/feasibility-gui/issues/416)
* Search engine updates – revised engine logic and search operation flow.
* Updated UI profile to support multiple value sets and criteria sets for feasibility [#425](https://github.com/medizininformatik-initiative/feasibility-gui/issues/425)
* Added feedback through the snackbar on profile edit [#448](https://github.com/medizininformatik-initiative/feasibility-gui/issues/448)
* Major overhaul of CSS and component layouts for improved consistency and responsiveness.  [#452](https://github.com/medizininformatik-initiative/feasibility-gui/issues/452), [#440](https://github.com/medizininformatik-initiative/feasibility-gui/issues/440)
* Removed unused and outdated configuration entries; Data Portal settings are now retrieved from the backend settings endpoint during application initialization. [#432](https://github.com/medizininformatik-initiative/feasibility-gui/issues/432)
* CRTDL display objects are now loaded from the backend at startup. [#455](https://github.com/medizininformatik-initiative/feasibility-gui/issues/455)
* Improved display of terminology titles. [#465](https://github.com/medizininformatik-initiative/feasibility-gui/issues/465)
* Implemented auto-save functionality in the data selection editor; profile changes are now saved automatically.  [#468](https://github.com/medizininformatik-initiative/feasibility-gui/issues/468)
* Added a selectable boolean to criteria-relative data to prevent adding elements to the cohort when not allowed.  [#482](https://github.com/medizininformatik-initiative/feasibility-gui/issues/482)
* Fixed UI crashes occurring when linking a reference in the data selection.  [#478](https://github.com/medizininformatik-initiative/feasibility-gui/issues/478)
* Added bulk search functionality for criteria [#460](https://github.com/medizininformatik-initiative/feasibility-gui/issues/460)
* Added bulk search support for `CodeableConcept` [#461](https://github.com/medizininformatik-initiative/feasibility-gui/issues/461)
* Introduced explanation tabs providing information about concepts, fields, references, terminology codes, time restrictions and token filters [#495](https://github.com/medizininformatik-initiative/feasibility-gui/issues/495)
* Snackbar notifications now display across the UI on user interaction [#470](https://github.com/medizininformatik-initiative/feasibility-gui/issues/470), [#476](https://github.com/medizininformatik-initiative/feasibility-gui/issues/476)
* Updated button naming convention to be action-oriented [#469](https://github.com/medizininformatik-initiative/feasibility-gui/issues/469)
* Redesigned tab component and query editor for improved usability and responsiveness [#388](https://github.com/medizininformatik-initiative/feasibility-gui/issues/388)
* Added dedicated tab to display and manage selected concepts [#477](https://github.com/medizininformatik-initiative/feasibility-gui/issues/477)
* Changed repository name from "feasibility-gui" to "dataportal-gui" to reflect broader functionality [#502](https://github.com/medizininformatik-initiative/feasibility-gui/issues/502)
* Added save, upload, and download functionality to the action bar by default across the UI [#463](https://github.com/medizininformatik-initiative/feasibility-gui/issues/463)
* Renamed data selection tab names in the query editor view [#501](https://github.com/medizininformatik-initiative/feasibility-gui/issues/501)
* Refactored the CRTDL translator to allow bulk upload of criteria and codeable concepts [#472](https://github.com/medizininformatik-initiative/feasibility-gui/issues/472)
* Added auto upgrade of CRTDL on upload [#545](https://github.com/medizininformatik-initiative/dataportal-ui/issues/545)
* Added auto upgrade of CCDL on upload [#548](https://github.com/medizininformatik-initiative/dataportal-ui/issues/548)


#### dataportal-backend

* #599 - Update UI profile model to allow support of multiple value sets by @michael-82 in https://github.com/medizininformatik-initiative/feasibility-backend/pull/600
* Settings endpoint was added to provide configuration settings to the GUI ([#663](https://github.com/medizininformatik-initiative/feasibility-backend/issues/663))
* Endpoint to retrieve all ui profiles was added ([#721](https://github.com/medizininformatik-initiative/feasibility-backend/issues/721))
* An endpoint was added to convert crtdl to a zip file with csv files ([#721](https://github.com/medizininformatik-initiative/feasibility-backend/issues/721))
* Relationship entries (parents/children/related_items) in terminology search now contain selectable, termcode and terminology attributes ([#664](https://github.com/medizininformatik-initiative/feasibility-backend/issues/664), [#734](https://github.com/medizininformatik-initiative/feasibility-backend/issues/734))
* #690 - Add exact search endpoint for criteria and for value sets by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/699
* Switch to PEM encoded client certificate for dsf broker by @EmteZogaf in https://github.com/medizininformatik-initiative/dataportal-backend/pull/741
* #664 - Include selectable boolean in /terminology/entry/{id}/relations response by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/694
* #721 - Change UiProfile handling by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/723
* Update dependency com.squareup.okhttp3:mockwebserver to v5.3.0 by @renovate[bot] in https://github.com/medizininformatik-initiative/dataportal-backend/pull/722
* #709 - Add endpoint to convert crtdl to csv zip by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/718
* #663 - Standardized API endpoint to serve configuration for the frontend by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/669
* #771 - Add extra variable for internal polling limit vs external (ui) polling limit by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/774
* #689 -  Improved Error Handling by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/769
* #836 - Dispatch queries asynchronously by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/837
* Ensure validator also validates against children fields by @juliangruendner in https://github.com/medizininformatik-initiative/dataportal-backend/pull/843
* #758 - Update Documentation by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/849
* #870 - Auto upgrade CRTDLs by @michael-82 in https://github.com/medizininformatik-initiative/dataportal-backend/pull/875
* Reconnect websocket to DSF after connection termination by @EmteZogaf in https://github.com/medizininformatik-initiative/dataportal-backend/pull/742
* Import all Certificates in PEM Files by @EmteZogaf in https://github.com/medizininformatik-initiative/dataportal-backend/pull/781
* #872 - Move Reconnector to Collector and do not reuse Websocket by @EmteZogaf in https://github.com/medizininformatik-initiative/dataportal-backend/pull/873

#### availability-updater

- Initial Release with Container build
- Download Ontology from fhir-ontology-generator repository
- Download availability reports from local fhir report server
- Update Availability based on ontology
- Update Availability on local elastic search
- Treat patient stratifier differently - calculate accross als statifier and map individually
- Make min required reports for availability update configurable
- Added oauth2 and basic auth support
- Added self-signed certificate support

#### Keycloak

#### Blaze (FHIR server for data and terminology service)

* Improve FHIR Search Performance for Multiple Params and Values ([#799](https://github.com/samply/blaze/issues/799))
* Fix Paging with FHIR Search _id Parameter ([#2953](https://github.com/samply/blaze/issues/2953))
* Prevent Cache Thrashing During Large Resource Scans ([#3086](https://github.com/samply/blaze/issues/3086))
* Improve Performance of FHIR Search Queries with 10k Values ([#3112](https://github.com/samply/blaze/issues/3112))
* Allow to Cache Larger CQL Expressions ([#3113](https://github.com/samply/blaze/issues/3113))
* Optimize DateTime Parsing ([#3064](https://github.com/samply/blaze/issues/3064))
* Remove Duplicate Search Params and Values ([#3036](https://github.com/samply/blaze/issues/3036))
* Implement _since for Patient $everything ([#1636](https://github.com/samply/blaze/issues/1636))
* Implement ValueSet References ([#110](https://github.com/samply/blaze/issues/110))
* Implement CQL Instance Expression for FHIR Types ([#3126](https://github.com/samply/blaze/issues/3126))
* Fail on Unsupported FHIR Search Modifier ([#2951](https://github.com/samply/blaze/issues/2951))
* Switch Resource Cache Sizing from Count to Memory-Based ([#3253](https://github.com/samply/blaze/issues/3253))
* Implement $cql Operation ([#3230](https://github.com/samply/blaze/issues/3230))
* Implement CQL Operator InCodeSystem ([#3157](https://github.com/samply/blaze/issues/3157))
* Implement Basic VCL Support ([#3275](https://github.com/samply/blaze/issues/3275))
* Offer Health Checks ([#3338](https://github.com/samply/blaze/issues/3338))
* Support Multiple Codings in Terminology Operations ([#3347](https://github.com/samply/blaze/issues/3347))
* Fix SNOMED CT CodeSystem Generation ([#3456](https://github.com/samply/blaze/issues/3456))
* Resolve Versions in Terminology Service ([#3470](https://github.com/samply/blaze/issues/3470))

#### TORCH

- Transfer script to FHIR DUP Server [#394](https://github.com/medizininformatik-initiative/torch/pull/394)
- Update Shipped Structure Definitions [#481](https://github.com/medizininformatik-initiative/torch/pull/481)
- Implement Conflict Handling in Consent [#513](https://github.com/medizininformatik-initiative/torch/pull/513)
- Increase WebFlux Buffer Size [#514](https://github.com/medizininformatik-initiative/torch/pull/514)
- Support nested Lists [#589](https://github.com/medizininformatik-initiative/torch/pull/589)
- Handle single consents [#478](https://github.com/medizininformatik-initiative/torch/pull/478)
- Add information about attributeGroup to resources [#525](https://github.com/medizininformatik-initiative/torch/pull/525)
- Support backbone reference resolve [#511](https://github.com/medizininformatik-initiative/torch/pull/511)
- Fix unsupported FHIR time types in consent check [#645](https://github.com/medizininformatik-initiative/torch/pull/645)
- Set required recorded field on Provenance resource [#662](https://github.com/medizininformatik-initiative/torch/pull/662)
- Fix Missing Default For Base Url [#673](https://github.com/medizininformatik-initiative/torch/pull/673)
- Fix Resource Cache Not Filtered After Reference Handling [#678](https://github.com/medizininformatik-initiative/torch/pull/678)
- Fix NPE in Date Parsing Crashes Consent Extraction [#679](https://github.com/medizininformatik-initiative/torch/pull/679)
- Fix NPE in collectReferences [#726](https://github.com/medizininformatik-initiative/torch/issues/726)
- Fix NPE in DateTimeReading [#696](https://github.com/medizininformatik-initiative/torch/issues/696)
- Fix Torch Not Retrying On Prematurely Closed [#701](https://github.com/medizininformatik-initiative/torch/issues/701)
- Add FAQ and Error Numbers for Lookup [#594](https://github.com/medizininformatik-initiative/torch/issues/594)
- Implement Job Manager [#659](https://github.com/medizininformatik-initiative/torch/issues/659)
- Fix Concurrency Issue In Batch Bundle Query Calls [#734](https://github.com/medizininformatik-initiative/torch/pull/734)
- Fix slice with coding not resolved correctly [#737](https://github.com/medizininformatik-initiative/torch/pull/737)
- Ensure Unexpandable concept does not shut down torch [#749](https://github.com/medizininformatik-initiative/torch/issues/749)
- Remove Torch Reference Restriction [#741](https://github.com/medizininformatik-initiative/torch/issues/741)
- Fix Filter Expansion Defaulting To Empty When Not Expandable [#769](https://github.com/medizininformatik-initiative/torch/issues/769)
- Fix: cascading delete not resolved correctly [#772](https://github.com/medizininformatik-initiative/torch/issues/772)
- Add Patient Params To Transfer To Dup Script [#584](https://github.com/medizininformatik-initiative/torch/issues/584)
- Adding Diagnostic Monad for Collecting Operation Outcomes  [#666](https://github.com/medizininformatik-initiative/torch/issues/666)
- Add Patient.identifier handling for traceability  [#772](https://github.com/medizininformatik-initiative/torch/issues/772)

#### FLARE

* Update Ontology to v4.0.0

#### FDE - Fhir-Data-Evaluator

* Update Documentation
* Make Obfuscation Count Configurable
* Fix UUID Not Set Correctly
* Add Resource Information on Failures
* Add Integration Tests with Hapi Fhir Server

#### aether

* Initialise project and add basic extraction and pipeline functionality
* Add TORCH support
* Add github pages documentation
* Add Pipeline steps including connected services: torch, wait, dimp, fhir-validation, flattening, send

#### fhir-pseudonymizer

* Add dataportal base DUP DIMP yaml
* Add fhir-pseudonymizer v2.25.0 from base [repository](https://github.com/miracum/fhir-pseudonymizer)
* Core used methods in dataportal context: redact, generalize, cryptoHash, keep

#### mii-fhir-validator

* Add initial service and connect to local terminology service
* Based on HL7 [validator cli project](https://confluence.hl7.org/spaces/FHIR/pages/35718580/Using+the+FHIR+Validator)
* Provides validator webservice /validateResource
* Includes package download and advisor file setup

#### fhir-flattener

* Wrapped pathling library ViewDefinition Runner
* Add ViewDefinition run operation
* Add support fro quantity extensions


## [5.4.6] - 2025-10-17

**minor fixes in v5.4.6**

- GUI
  - Fixed missing token and date filters when loading a CRTDL.
  - Fixed an issue where unmatched fields in a loaded CRTDL were not properly removed
  - Corrected sorting behavior of criteria.

- ONTOLOGY
  - Allow multiple value set references in UI profile attributes 
  - Ensure backbone references are selectable
  - Adapt generator to new MII CDS ICU module version
  - Restrict allowed units of age criterion class

- TORCH
  - Do not write empty ndjson
  - Increase WebFlux Buffer Size
  - Fix Literal Quotes in Env Vars

 ### Updates to

- GUI to [6.3.7](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.3.7)
- BACKEND to [7.5.1](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.5.1)
- ONTOLOGY to [3.9.1](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.9.1)
- TORCH to [1.0.0-alpha.11](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.11)

## [5.4.5] - 2025-09-24

**minor fixes in v5.4.5**

- TORCH
  - Update to new structureDefinitions

- GUI
  - Fix allow deleting of dse feature filter
  - Prevent field tree from collapsing
  - Ensure Patient profile always part of DSE

- ONTOLOGY
 - Fix profile resolution
 - Fix Orphanet and Ops translations
 - Fix availability measure

- BACKEND
 - Search in original display
 - Display all filter options

 ### Updates to

- GUI to [6.3.6](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.3.6)
- BACKEND to [7.5.0](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.5.0)
- ONTOLOGY to [3.9.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.9.0)
- TORCH to [1.0.0-alpha.10](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.10)
- Blaze to [1.1.2](https://github.com/samply/blaze/releases/tag/v1.1.2)

### New Features

- GUI, ONTOLOGY, BACKEND
  - Updated UI profile to support multiple value sets and criteria sets for feasibility


## [5.4.4] - 2025-08-25

**minor fixes in v5.4.4**

- TORCH
  - Add Permit Type and Consent Status in Consent Calculation

### New Features

- GUI
  - Changed description of Feature Selection
- TORCH
  - Fix Torch does not provide Base URL in Status Response

### Ontology

This release is based on ontology version [v3.8.3](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.8.3)

### Updates to

- GUI to [6.3.5](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.3.5)
- TORCH to [1.0.0-alpha.8](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.8)


## [5.4.3] - 2025-08-18

### New Features

- GUI
  - Infinite scrolling – implemented for CodeableConcept search, Criteria search, and Reference search
  - Support loading of query by id via url params
  - Add Link to Proposal Portal
  - Display tree icon next to each search result

### Ontology

This release is based on ontology version [v3.8.3](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.8.3)

### Updates to

- GUI to [6.3.4](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.3.4)


## [5.4.2] - 2025-08-14

### New Features

- Ontology
  - Added modules MII CDS Study, MII CDS Pathology, and MII CDS Imaging to DSE profile selection
  - Updated translations

### Ontology

This release is based on ontology version [v3.8.3](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.8.3)

### Updates to

- Backend to [7.4.0](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.4.0)
- Ontology to [3.8.3](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.8.3)


## [5.4.1] - 2025-08-07

**minor fixes in v5.4.1**

- TORCH:
  - Transfer script to FHIR DUP Server
  - Fix Bundle PUT URL Not Set To Relative URL
  - Fix ProfileMustHaveChecker Does Not Strip Versions

### Ontology

This release is based on ontology version [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)

### Updates to

- TORCH to [1.0.0-alpha.7](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.7)


## [5.4.0] - 2025-07-24


### Ontology

Changed FROM [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0) to [v3.8.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.8.0)

#### Major Ontology Updates

* Update display generation for value definitions of criteria by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/289
* Implement Cause of Death criteria class for cohort selection ontology by @paulolaup in https://github.com/medizininformatik-initiative/fhir-ontology-generator/pull/290


### Updates since last Major

|Component|From|To|
|--|--|--|
|UI|[v6.2.0](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.2.0)|[v6.3.3](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.3.3)|
|Backend|[v7.1.1](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.1.1)|[v7.3.0](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.3.0)|
|Blaze|[v1.0.0](https://github.com/samply/blaze/releases/tag/v1.0.0)|[v1.0.4](https://github.com/samply/blaze/releases/tag/v1.0.4)|
|Keycloak|keycloak/keycloak:26.2|quay.io/keycloak/keycloak:26.3.1|
|TORCH|[1.0.0-test2](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-test2)|[1.0.0-alpha.6](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.6)|
|FLARE|[2.5.0](https://github.com/medizininformatik-initiative/flare/releases/tag/v2.5.0)|[2.6.0](https://github.com/medizininformatik-initiative/flare/releases/tag/v2.6.0)|
|FDE|[1.2.0](https://github.com/medizininformatik-initiative/fhir-data-evaluator/releases/tag/v1.2.0)|[1.3.1](https://github.com/medizininformatik-initiative/fhir-data-evaluator/releases/tag/v1.3.1)|


### Major Changes since last Major

#### UI

* Preloaded criteria filter, criteria search results and data selection profiles before page load using Angular route resolver [#415](https://github.com/medizininformatik-initiative/feasibility-gui/issues/415)
* **About Page** with system version information (UI, Backend, Ontology) [#403](https://github.com/medizininformatik-initiative/feasibility-gui/issues/403)
* Updated **language files** in `src/assets/i18n` [#393](https://github.com/medizininformatik-initiative/feasibility-gui/issues/393), [#399](https://github.com/medizininformatik-initiative/feasibility-gui/issues/399), [#400](https://github.com/medizininformatik-initiative/feasibility-gui/issues/400)
* Change download behaviour of Cohort selection ([#395](https://github.com/medizininformatik-initiative/feasibility-gui/issues/395))
* Query without data selection is not saveable anymore ([#396](https://github.com/medizininformatik-initiative/feasibility-gui/issues/396))
* Fix for mandatory patient feature is added to DSE on query load ([#394](https://github.com/medizininformatik-initiative/feasibility-gui/issues/394))
* Checkbox for "Only if referenced" is only be visible if feature is referenced ([#397](https://github.com/medizininformatik-initiative/feasibility-gui/issues/397))

#### Backend

* #523  - Admin user should be able to read all queries by @michael-82 in https://github.com/medizininformatik-initiative/feasibility-backend/pull/524
* #516 - provide export of CQL "translation" by @michael-82 in https://github.com/medizininformatik-initiative/feasibility-backend/pull/528
* #537 - Move openai documentation to default api path by @michael-82 in https://github.com/medizininformatik-initiative/feasibility-backend/pull/538
* Implement FHIR Async Request Pattern for Direct Broker using CQL by @EmteZogaf in https://github.com/medizininformatik-initiative/feasibility-backend/pull/539
* #544 - Move cql config parameters in application yml by @michael-82 in https://github.com/medizininformatik-initiative/feasibility-backend/pull/545
* #540 - Resultsize missing in dataquery list via by-user endpoint by @michael-82 in https://github.com/medizininformatik-initiative/feasibility-backend/pull/541

#### Keycloak

* Changed from Keycloak image to quay.io image to ensure use of the official, up-to-date container maintained by the Keycloak team.

#### Blaze

* Fix Consent Resource policyRule Property ([#2700](https://github.com/samply/blaze/issues/2700))
* Support Resolving Relative References in Transaction Bundles ([#2734](https://github.com/samply/blaze/issues/2734))
* Search for text/cql Content in Library ([#2718](https://github.com/samply/blaze/issues/2718))
* Fix Query Sort in CQL ([#1315](https://github.com/samply/blaze/issues/1315))

#### TORCH

* First alpha Version release, which is released as part of the deployment
* For features see TORCH Wiki

#### FLARE

* Update Ontology to v3.8.0 ([#294](https://github.com/medizininformatik-initiative/flare/issues/294))

#### FDE - Fhir-Data-Evaluator

* Add backpressure handling
* Add additional logging
* Add Option to Obfuscate Stratifier Results

## [5.3.4] - 2025-06-20

**minor fixes in v5.3.4**

- Backend:
  - Fix admin user was not able to read all queries

### Ontology

This release is based on ontology version [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)

### Updates to

- Blaze to [1.0.2](https://github.com/samply/blaze/releases/tag/v1.0.2)
- TORCH to [1.0.0-alpha.5](https://github.com/medizininformatik-initiative/torch/releases/tag/v1.0.0-alpha.5)


## [5.3.3] - 2025-06-06

**minor fixes in v5.3.3**

- Backend:
  - Fix admin user was not able to read all queries

### Ontology

This release is based on ontology version [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)

### Updates to

- backend to [v7.1.2](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.1.2)


## [5.3.2] - 2025-05-30

**minor fixes in v5.3.2**

- Backend:
  - Fix interval syntax error

### Ontology

This release is based on ontology version [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)


## [5.3.1] - 2025-05-30

**minor fixes in v5.3.1**

- GUI:
  - Add missing PatientProfile URL in deploy configuration

### Ontology

This release is based on ontology version [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)


## [5.3.0] - 2025-05-28

**minor fixes in v5.3.0**

- Backend:
  - Fix - creating dataquery with filterdate causes error
  - Fix - reading the crtdl part of a dataquery without cohortDefinition fails
  - Fix - error reading query list
  - Fix - missing Display Information for Parents and Children
- GUI:
  - Increased ElasticSearch visualization limit from 20 to 50 matches
  - Adjusted CSS for indentation in tree view
  - Switch date display to european format

### New Features

- Backend:
  - Extend api to save and load cohort and dataselection
  - Generate crtdl csv file
  - Change configurable time intervals to ISO 8601 durations
- GUI:
  - New save dialog with checkboxes for cohort and data selection
  - Added new editor pages for Criterion and Profile
  - Added support for single feature patient profiles
  - Implemented loading of reference profile lists
  - Switch to backend API v5

### Ontology

This release is based on ontology version [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)

### Updates to

- backend to [v7.1.1](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v7.1.1)
- ontology to [v3.7.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.7.0)
- UI to [v6.2.0](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.2.0)
- Blaze to [v1.0.0](https://github.com/samply/blaze/releases/tag/v1.0.0)


## [5.2.4] - 2025-03-21

**minor fixes in v5.2.4**

- GUI:
  - Prevent constant openings of modal after downloading query

### Ontology

This release is based on ontology version [v3.2.2](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.2)

### Updates to

- UI to [v6.0.10](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.0.10)


## [5.2.3] - 2025-03-19

### Special notes

Set UI to previously stable version 6.0.6 (https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.0.6)

### Ontology

This release is based on ontology version [v3.2.2](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.2)

### Updates to

- backend to [v6.2.2](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v6.2.2)
- ontology to [v3.2.2](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.2)
- blaze frontend to match server version, bot to [0.33](https://github.com/samply/blaze/tree/v0.33.0)

### Downgrades

- UI to 6.0.6 (https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.0.6)


## [5.2.2] - 2025-03-18

**minor fixes**

- Ontology:
  - Fix - do not set reference fields as recommended for data selection

### Ontology

This release is based on ontology version [v3.2.2](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.2)

### Updates to

- backend to [v6.2.2](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v6.2.2)
- ontology to [v3.2.2](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.2)


## [5.2.1] - 2025-03-17

**minor fixes in v5.2.1**

- Ontology:
  - Revert changes in FHIRSearch mapping to fix incompatibility with FLARE

### Ontology

This release is based on ontology version [v3.2.1](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.1)

### Updates to

- backend to [v6.2.1](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v6.2.1)
- ontology to [v3.2.1](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.1)


## [5.2.0] - 2025-03-14

**minor fixes in v5.2.0**

- GUI:
  - Details counter gets incremented correctly
  - Combined consent is set in downloaded CCDL
- Backend:
  - Encounter Module fixed by fixed typing in ontology

### New Features

- Backend:
  - Provide an endpoint for version information, accessible at path `/actuator/info`
- GUI:
  - Translation for consent text

### Ontology

This release is based on ontology version [v3.2.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.0)

### Updates to

- backend to [v6.2.0](https://github.com/medizininformatik-initiative/feasibility-backend/releases/tag/v6.2.0) and within sq2cql to [v1.0.0](https://github.com/medizininformatik-initiative/sq2cql/releases/tag/v1.0.0)
- ontology to [v3.2.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.2.0)
- UI to [v6.0.8](https://github.com/medizininformatik-initiative/feasibility-gui/releases/tag/v6.0.8)
- Blaze to [v0.33](https://github.com/samply/blaze/releases/tag/v0.33.0)


## [5.1.1] - 2025-03-03

**minor fixes in v5.1.1**

- Backend Bugfixes: Improve elastic search query for better results, fix initial counter value of remaining result details views

### known bugs

- Encounter Module faulty at sq2cql translation and therefore non functioning (CQL)

### Ontology

This Release is based on ontology Version [v3.1.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.1.0)

### Updates to

- backend


## [5.1.0] - 2025-02-18

**minor fixes in v5.1.0**

- sq2cql and ontology were updated to handle time restrictions by type correctly
- UI Bugfixes: Remove hashes from feasibility detail results, Fixed error message display, Resolve inconsistency between summary and details results

### New Features

- Added translations
- Added new CDS modules to dataselection - see ontology release

### known bugs

- Encounter Module faulty at sq2cql translation and therefore non functioning (CQL)

### Ontology

This Release is based on ontology Version [v3.1.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.1.0)

### Updates to

- backend and within sq2cql
- ontology
- UI


## [5.0.2] - 2025-02-03

**minor fixes in v5.0.2**

- sq2cql was updated to handle consent MedicationStatement and MedicationRequest correctly

### known bugs

- Encounter Module faulty at sq2cql translation and therefore non functioning (CQL)

### Ontology

This Release is based on ontology Version [v3.0.1](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.0.1)

### no updates to

- Everything except backend


## [5.0.1] - 2024-12-18

**minor fixes in v5.0.1**

- Ontology contained multiple instances of the same codes but lacked others -> fixed, v3.0.1
- sq2cql was updated to handle consent correctly
- UI was unable to save cohort selections -> fixed

### known bugs

- Encounter Module faulty at sq2cql translation and therefore non functioning (CQL)
- Medication Statement, Medication request faulty at sq2cql level and therefore non functioning (CQL)

### Ontology

This Release is based on ontology Version [v3.0.1](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.0.1)
Flare contains new ontology

### no updates to

- Torch
- FDE


## [5.0.0] - 2024-11-21

### Ontology

This Release is based on ontology Version [v3.0.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v3.0.0)


### Overall

- Updated all components to new versions
- Made FLARE execute-cohort endpoint only available on local docker network and new FLARE version makes enabling execute-cohort endpoint configurable
- Added Fhir-Data-Evaluator (FDE) to triangle

### Features

| Feature | Affected Components |
| -- | -- |
|UI Re-Design, Restructuring of Code|UI, Backend|
|Extended Criteria Search (Elastic Search)|UI, Backend, Ontology Generation|
|Add OAuth2 to triangle components|TORCH, FLARE|
|Added Dataselection and Extraction |UI, Backend, Ontology Generation, TORCH|
|Migrated from Mapping code system tree strcture to poly tree structure to support non strict hierarchical code systems like sct |UI, Backend, Ontology Generation, TORCH, FLARE|
|Loading and displaying of criteria availability |UI, Backend, Ontology Generation|
|Added new modules and Updated Ontology|UI, Backend, Ontology Generation, FLARE, sq2cq, TORCH|


## [5.0.0-alpha.1] - 2024-11-15

### Overall

- Updated all components to new versions
- Made FLARE execute-cohort endpoint only available on local docker network and new FLARE version makes enabling execute-cohort endpoint configurable


## [5.0.0-alpha] - 2024-10-21

### Features

| Feature | Affected Components |
| -- | -- |
|UI Re-Design, Restructuring of Code|UI, Backend|
|Extended Criteria Search (Elastic Search)|UI, Backend, Ontology Generation|
|Add OAuth2 to triangle components|TORCH, FLARE|
|Added Dataselection and Extraction |UI, Backend, Ontology Generation, TORCH|
|Migrated from Mapping code system tree strcture to poly tree structure to support non strict hierarchical code systems like sct |UI, Backend, Ontology Generation, TORCH, FLARE|
|Loading and displaying of criteria availability |UI, Backend, Ontology Generation|

### Overall

- Updated all components to new versions
- Added TORCH component for data selection and extraction in the triangle


## [4.1.0] - 2024-07-16

### Overall

- Changed to context configuration (installing using one domain) for default setup
- Added option to switch between subdomain and context setup


## [4.0.0] - 2024-07-01

### Overall

- Updated components and underlying libraries to the new versions and added new components:
  - Portal: gui `5.0.0`, backend `5.0.1`, keycloak `25.0`
  - Triangle:  flare `2.3.0`, blaze `0.28`, keycloak `25.0`
- Components above are based on ontology  ([2.2.0](https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/tag/v2.2.0))
- Changed to subdomain configuration for default setup
- Separated portal webserver from UI for default deploy
- Removed AKTIN

### Features

| Feature | Affected Components |
| -- | -- |
|Improved support for referenced criteria|UI|
|Refactored Code Base|UI|
|Add OAuth2|DSF Feasibility Plugin|
|Add frontend|Blaze|
|Add dynamic indexing|Blaze|
|Add oAuth to direct broker for CQL|backend|

### Bugfix

| Bug | Affected Components |
| -- | -- |
|Fix Translation on Expanded Criteria with Reference Attribute Filters|sq2cql|
|Add Basic Auth to direct broker|backend|

### Removed

- Removed AKTIN support


## [3.2.0] - 2023-11-17

### Overall

- Updated gui, backend and flare components and underlying libraries to the new versions
- Adjusted readme to reflect changes in the underlying components and added Info about Blaze re-indexing
- Updated Ontology to newest version

### Bugfix

| Bug | Affected Components |
| -- | -- |
|Fixed consent querying|UI, backend, Ontology, sq2cql, FLARE, Blaze|
|Fixed CQL large query generation|sq2cql|
|Added newest missing search params to Blaze in this repository |Blaze|

## [3.1.0] - 2023-11-09

### Overall

- Updated all components and underlying libraries to the new versions
- Adjusted readme to reflect changes in the underlying components

### Features

| Feature | Affected Components |
| -- | -- |
|Improved support for referenced criteria|UI, backend, Ontology, sq2cql, FLARE, Blaze|
|Improved saving and loading of templates and saved queries|UI, backend|
|Make UI category order configurable|UI, backend|
|Improved Dataselection: added support for required criteria, allow selecting of any term tree node, |UI|
|Updated sq2cql to new ontology version|backend, sq2cql, Ontology, Blaze|
|Allow querying without value filter according to ontology ui_profiles optional attribute|UI, backend, Ontology|
|Improved error handling|UI, backend|


## [3.0.0] - 2023-10-08

### Overall

- Updated all components and underlying libraries to the new versions
- Updated all components to version compatible with ontology version 2.0
- Adjusted readme to reflect changes in the underlying components

### Features

| Feature | Affected Components |
| -- | -- |
|Added support for referenced criteria|UI, backend, Ontology, sq2cql, FLARE|
|Added support for composite search parameters|UI, SQ, Ontology, sq2cql, FLARE|
|Updated to new DSF version v1.0.0 compatible with new DSF verison v1.x | Backend, DSF feasibility plugin|
|Added Dateselection|UI|
|Update ontology to new ontology generation and added ontology to images directly| Ontology, Backend, FLARE|
|Added encrypted result logging| Backend|
|Add support for self-signed certificates| Backend, FLARE, DSF feasibility plugin |


## [2.1.0] - 2023-07-25

### Overall

- Updated AKTIN Client to 1.6.0: Fix websocket timeout and improve error handling  - <https://github.com/medizininformatik-initiative/feasibility-aktin-plugin/releases/tag/v1.6.0>
- Updated FLARE to 1.0: Fix Execution Operation - <https://github.com/medizininformatik-initiative/flare/releases/tag/v1.0.0>
- Updated Blaze to 0.22: implements $everything, adds basic frontend, Support for Custom Search Parameters <https://github.com/samply/blaze/releases/tag/v0.22.0>
- Added Troubleshooting specific for triangle
- Update testdata repo from MII


## [2.0.0] - 2023-03-29

### Overall

- Updated all components and underlying libraries to the new versions
- Updated UI to angular 15
- Updated keycloak to 21.0
- Updated nginx to 1.23
- Refactored deploy repository - removed DSF from this deployment and added reference to DSF deployment in Readme
- Removed hapi fhir-server from deployment

### Features

| Feature | Affected Components |
| -- | -- |
|Added calculated criterion age|Ontology, Sq2cql, FLARE|
|Improved at site obfuscation|DSF Feasibility Plugin, AKTIN Client|
|Added SQ query import and export|UI|
|Improved FHIR query execution and result caching |FLARE|
|Update Consent to new search params and add central MII consent query|UI, Ontology|
|Update ontology to newest KDS version| Ontology|
|Update AKTIN client to new version, move query handling to Java plugin and add query validation|AKTIN client|
|SQ query validation|Backend, AKTIN client|
|Add CQL execution to direct broker| Backend|

### Security and Privacy

| Feature | Affected Components |
| - | - |
|Added extra security measures, which restrict number queries a user can send and results a user can view|UI, Backend|
|Improved at site obfuscation|DSF Feasibility Plugin, Aktin Client|
|Hard rate limit at sites for AKTIN and DSF feasibility plugins|DSF feasibility plugin, AKTIN Client|
|Query results are no longer persisted and only kept in memory for a configurable amount of time|Backend|
|Delete query results from central DSF and AKTIN broker on collection|Backend|
|User blacklisting if too many queries are sent in a given time|Backend|

## [1.6.0] - 2022-09-08
