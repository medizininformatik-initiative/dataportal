# FDPG Data Portal

The FDPG Data Portal is a user interface for researchers to:

1. Search a metadata catalog of criteria and data items
2. Define cohorts based on inclusion and exclusion criteria
3. Execute feasibility queries based on the cohort definitions
4. Define a Data Extraction


The portal is installed centrally at the FDPG as the central data hub. However it can also be installed at a site to
provide local data portal functionality.

## Local installation

The local installation of the portal, even though highly recommended, is not a preqrequisite to participate in FDPG DUP projects.

### Pre-requisites

The dataportal requires:

- A proxy for tls termination for both the UI and the Backend
- A oauth2 service (keycloak) for both the UI and Backend

Both of which are included in the example installation - see [below](#example-data-portal-installation).

### Example Data Portal Installation

An example installation can be found [here](https://github.com/medizininformatik-initiative/dataportal/tree/main/data-portal)

### Data Portal Components

The components of the portal are packaged as one, and the UI and backend of the portal have to be installed as one.


| Reference Component         | Component                                             | Use | Documentation                                                                                                                                                                                                                                        |     Description                                                                                                                    |
| ------------------------- | ---------------------------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| feasibility-ui                     | Dataportal UI                                         |                 | [Overview](https://github.com/medizininformatik-initiative/feasibility-gui), | Dataportal UI                                                            |
| feasibility-backend                     | Dataportal Backend                                       |                 | [Overview](https://github.com/medizininformatik-initiative/feasibility-backend), | Dataportal Backend                                                            |
