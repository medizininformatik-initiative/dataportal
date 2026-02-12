#!/bin/bash
# shellcheck disable=SC2016

curl --request POST \
  --url 'http://localhost:8088/fhir/ViewDefinition/$run' \
  --header 'accept: text/csv' \
  --header 'content-type: application/fhir+json' \
  --data '{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "viewDefinition",
      "resource": {
        "name": "conds",
        "resource": "Condition",
        "resourceType": "ViewDefinition",
        "select": [
          {
            "column": [
              {
                "path": "Condition.code.coding.where(system='\''http://fhir.de/CodeSystem/bfarm/icd-10-gm'\'').code",
                "name": "codeIcd10"
              },
              {
                "path": "Condition.code.coding.where(system='\''http://fhir.de/CodeSystem/bfarm/icd-10-gm'\'').code",
                "name": "codeAlphaId"
              },
              {
                "path": "Condition.recordedDate",
                "name": "recordedDate"
              },
              {
                "path": "Condition.clinicalStatus.coding.code",
                "name": "clinicalStatus"
              },
              {
                "path": "Condition.verificationStatus.coding.code",
                "name": "verificationStatus"
              }
            ]
          }
        ]
      }
    },
    {
      "name": "resources",
      "resource": {
        "resourceType": "Condition",
        "id": "mii-exa-test-data-patient-1-diagnose-2",
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
              "version": "2023",
              "code": "H67.1",
              "display": "Otitis media bei anderenorts klassifizierten Viruskrankheiten"
            }
          ]
        },
        "subject": {
          "reference": "Patient/mii-exa-test-data-patient-1"
        },
        "recordedDate": "2024-02-21"
      }
    },
    {
      "name": "resources",
      "resource": {
        "resourceType": "Condition",
        "id": "mii-exa-test-data-patient-1-diagnose-1",
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
              "extension": [
                {
                  "url": "http://fhir.de/StructureDefinition/icd-10-gm-mehrfachcodierungs-kennzeichen",
                  "valueCoding": {
                    "system": "http://fhir.de/CodeSystem/icd-10-gm-mehrfachcodierungs-kennzeichen",
                    "code": "†"
                  }
                },
                {
                  "url": "http://fhir.de/StructureDefinition/seitenlokalisation",
                  "valueCoding": {
                    "system": "https://fhir.kbv.de/CodeSystem/KBV_CS_SFHIR_ICD_SEITENLOKALISATION",
                    "code": "B",
                    "display": "beiderseits"
                  }
                },
                {
                  "url": "http://fhir.de/StructureDefinition/icd-10-gm-diagnosesicherheit",
                  "valueCoding": {
                    "system": "https://fhir.kbv.de/CodeSystem/KBV_CS_SFHIR_ICD_DIAGNOSESICHERHEIT",
                    "code": "G",
                    "display": "gesicherte Diagnose"
                  }
                }
              ],
              "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
              "version": "2023",
              "code": "B05.3"
            },
            {
              "system": "http://fhir.de/CodeSystem/bfarm/alpha-id",
              "version": "2023",
              "code": "I29578",
              "display": "Masern mit Otitis"
            },
            {
              "system": "http://snomed.info/sct",
              "version": "http://snomed.info/sct/900000000000207008/version/20230731",
              "code": "13420004",
              "display": "Post measles otitis media (disorder)"
            }
          ]
        },
        "subject": {
          "reference": "Patient/mii-exa-test-data-patient-1"
        },
        "recordedDate": "2024-02-21"
      }
    }
  ]
}'
