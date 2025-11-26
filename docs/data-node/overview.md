# FDPG Data Node

The FDPG Data Node contains software necessary to support data use projects at each side.

This repository has two aims:

First, it provides the documentation for a reference DUP pipeline and DUP support services with suggested software in specific versions, which have been
curated and tested by the FDPG team to work together.

Second, it provides an example installation, which is configured to be run on one machine, to allow setting it up for development, software review and to give an
example of how the components interact with each other and how they have to be configured in an example scenario.

It is important to note that each component can be run by itself and independently of the other components as long as all the interfaces this component 
is connecting to are provided at the site.

This means that each reference component can be exchanged for an equivalent in-house or purchased component.

Further the DUP pipeline is built in a way that the output of each step is saved in files to allow easy integration with other tools or services and branching off at any step

## Data Node Architecture

The typical architecture of a data node can be found [here](architecture.md)

## Data Node DUP pipeline

The typical DUP pipeline is described [here](dup-pipeline.md)


## Data Node Services

| Reference Service         | Service                                             | Use | Documentation                                                                                                                                                                                                                                        |     Description                                                                                                                    |
| ------------------------- | ---------------------------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Blaze                     | Fhir Server                                          |                 | [Overview](https://samply.github.io/blaze/), [Deployment](https://samply.github.io/blaze/deployment/full-standalone.html), [Configuration](https://samply.github.io/blaze/deployment/environment-variables.html)                                     | Fast FHIR Server with internal CQL engine for patient research data                                                            |
| Blaze                     | Terminology Server                                   |                 | [Overview](https://samply.github.io/blaze/), [Deployment](https://samply.github.io/blaze/terminology-service.html), [Configuration](https://samply.github.io/blaze/deployment/environment-variables.html)                                            | Fast Terminology Server                                                                                                        |
| fhir-data-evaluator (FDE) | FHIR data Analyser                                   | [Use Documentation](fhir-data-evaluator.md)| [Documentation](https://github.com/medizininformatik-initiative/fhir-data-evaluator)                                                                                                                                                                 | Given a Measure as input stratifies the data in the FHIR server and outputs a MeasureReport with the calculated stratification |
| flare                     | FHIR Search feasibility and cohort execution service |                 | [Documentation](https://github.com/medizininformatik-initiative/flare)                                                                                                                                                                               | Calculates feasbility cohort sizes and extracts cohorts (lists of patient IDs) based on a CCDL                                 |
| TORCH                     | FHIR Data Extractor                                  |                 | [Overview](https://medizininformatik-initiative.github.io/torch/), [Deployment](https://medizininformatik-initiative.github.io/torch/getting-started.html), [Configuration](https://medizininformatik-initiative.github.io/torch/configuration.html) | Given a CRTDL extracts patient data as bundles in .ndjson files                                                                |
| fhir-pseudonymizer        | FHIR DIMP service                                    |                 | [Documentation](https://github.com/miracum/fhir-pseudonymizer)                                                                                                                                                                                       | Given FHIR bundles as input applies pre-configured DIMP functions                                                              |
| mii-fhir-validator        | FHIR Validation                                      |                 | Still missing                                                                                                                                                                                                                                        | TOOl still missing – repository here                                                                                           |
| fhir-flattener            | Webservice SqlOnFhir ViewDefinition Runner           |                 | [Documentation](https://github.com/medizininformatik-initiative/fhir-flattener)                                                                                                                                                                      | Wraps the Pathling library into a lightweight ViewDefinition runner                                                            |
| aether                    | Data Use Project Pipeline Coordination Tool          |                 | [Documentation](https://github.com/medizininformatik-initiative/aether)                                                                                                                                                                              | Built to process DUP projects from pipeline.yml + CRTDL                                                                        |
