# Changelog

All notable changes to this project will be documented in this file.

## Component specific changes

Please refer to the respective repositories for a more in depth changelog of single components:

|Component|Link|
|--|--|
|Dataportal UI|<https://github.com/medizininformatik-initiative/dataportal-ui>|
|Dataportal Backend|<https://github.com/medizininformatik-initiative/dataportal-backend>|
|Dataportal Availability Updater|<https://github.com/medizininformatik-initiative/availability-updater>|
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
