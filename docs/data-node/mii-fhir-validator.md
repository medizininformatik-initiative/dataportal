# MII FHIR Validator

A locally deployable FHIR validation service. This service includes:

The FHIR Validator as a local HTTP service
Blaze terminology service (default, no authentication required)
Support for offline Implementation Guides

The aim of this validator is to create a validator, pre-loaded with packages from the MII, so that validation is harmonized accross the MII sites.

## Configuration

For the general configuration of the validator [see](https://github.com/medizininformatik-initiative/mii-fhir-validator).

Note that in order for the validator to function properly a terminology server needs to be set up, which contains all the relevant terminologies.

We provide a reference implementation [here](https://github.com/medizininformatik-initiative/dataportal/tree/main/data-node/terminology-server).

## Using the validator

the validator is created as a web service, which can be used to validate resources.

It does this by exposing a `validateResource` endpoint.

For additional information refer to the [original repository](https://github.com/medizininformatik-initiative/mii-fhir-validator).


Example call to validate resource endpoint:

```curl
curl --request POST \
  --url http://localhost:8080/validateResource \
  --header 'accept: application/fhir+json' \
  --header 'content-type: application/fhir+json' \
  --data '{
  "resourceType": "Condition",
  "id": "mii-condition-example-1",
  "meta": {
    "profile": [
      "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
    ]
  },
  "clinicalStatus": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
        "code": "active"
      }
    ]
  },
  "verificationStatus": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
        "code": "confirmed"
      }
    ]
  },
  "code": {
    "coding": [
      {
        "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
        "version": "2024",
        "code": "I50.01"
      }
    ]
  },
  "subject": {
    "reference": "Patient/mii-patient-example-1"
  },
  "recordedDate": "2024-01-15T10:30:00+01:00",
  "extension": [
    {
      "url": "http://hl7.org/fhir/StructureDefinition/condition-assertedDate",
      "valueDateTime": "2024-01-15"
    }
  ]
}'
```
