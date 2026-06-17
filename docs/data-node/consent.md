# Consent

The DUP Pipeline calculates consent based on the description [here](https://medizininformatik-initiative.github.io/torch/implementation/consent.html)

In the standard use case the following addition to the cohort part of the CRTDL will extract consents for central analysis while considering retrospective consent:

<details>
<summary>CRTDL insert: Consent for central analysis</summary>

```json
[
    [
        {
            "termCodes": [
                {
                    "code": "2.16.840.1.113883.3.1937.777.24.5.3.8",
                    "display": "MDAT wissenschaftlich nutzen EU DSGVO NIVEAU",
                    "system": "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3",
                    "version": "1.0.7"
                }
            ],
            "context": {
                "code": "Einwilligung",
                "display": "Einwilligung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            }
        }
    ],
    [
        {
            "termCodes": [
                {
                    "code": "2.16.840.1.113883.3.1937.777.24.5.3.6",
                    "display": "MDAT erheben",
                    "system": "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3",
                    "version": "1.0.7"
                }
            ],
            "context": {
                "code": "Einwilligung",
                "display": "Einwilligung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            }
        }
    ],
    [
        {
            "termCodes": [
                {
                    "code": "2.16.840.1.113883.3.1937.777.24.5.3.6",
                    "display": "MDAT erheben",
                    "system": "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3",
                    "version": "1.0.7"
                }
            ],
            "context": {
                "code": "Einwilligung",
                "display": "Einwilligung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            }
        },
        {
            "termCodes": [
                {
                    "code": "2.16.840.1.113883.3.1937.777.24.5.3.46",
                    "display": "MDAT retrospektiv wissenschaftlich nutzen EU DSGVO NIVEAU",
                    "system": "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3",
                    "version": "1.0.7"
                }
            ],
            "context": {
                "code": "Einwilligung",
                "display": "Einwilligung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            }
        },
        {
            "termCodes": [
                {
                    "code": "2.16.840.1.113883.3.1937.777.24.5.3.45",
                    "display": "MDAT retrospektiv speichern verarbeiten",
                    "system": "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3",
                    "version": "1.0.7"
                }
            ],
            "context": {
                "code": "Einwilligung",
                "display": "Einwilligung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            }
        }
    ]
]
```

</details>

Full example CRTDL [here](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/aether/queries/example-crtdl-consent.json)

Based on this input, TORCH will extract resources and check each resource against the consent period. It is important to verify this calculation against site-specific data using samples from the extraction.


## Verifying Consent

Take a random extracted resource from a patient bundle (job folder = import) or the CSV (job folder = csv).


**Example Condition resource from a extraction bundle:**


<details>
<summary>Condition resource from patient bundle</summary>

```json
{
    "resourceType": "Condition",
    "id": "mii-exa-test-data-patient-9-diagnose-1",
    "meta": {
        "profile": [
            "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
        ]
    },
    "code": {
        "coding": [
            {
                "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                "version": "2024",
                "code": "N83.2"
            },
            {
                "system": "http://fhir.de/CodeSystem/bfarm/alpha-id",
                "version": "2024",
                "code": "I20743",
                "display": "Ovarialzyste"
            },
            {
                "system": "http://snomed.info/sct",
                "version": "http://snomed.info/sct/900000000000207008/version/20230731",
                "code": "79883001",
                "display": "Cyst of ovary (disorder)"
            }
        ]
    },
    "subject": {
        "reference": "Patient/mii-exa-test-data-patient-9"
    },
    "recordedDate": "2024-02-20"
}
```
</details>

**Example row from a Condition CSV:**

```
id,patient,...,Condition_recordedDate,...
mii-exa-test-data-patient-9-diagnose-1,Patient/mii-exa-test-data-patient-9,...,2024-02-20,...
```

> [!INFO]
> Note that if you are using DIMP in your pipeline you cannot easily use the CSV to check your consent against, as the flattening comes after the DIMP step, which means that all the IDs (cryptohashed) and identifier (re-pseudonymized) will already be changed.

**Step 1 — Extract the consent-relevant date**

The date field to use depends on the resource type. The mapping is defined [here](https://github.com/medizininformatik-initiative/torch/blob/main/mappings/type_to_consent.json). For `Condition`, use `recordedDate` → in this example: `2024-02-20`

**Step 2 — Fetch the patient's consent**

```
GET http://fhir-base-url/fhir/Consent?patient=mii-exa-test-data-patient-9&_format=json
```

**Step 3 — Check provision `.6` (MDAT erheben)**

Find the provision with code `2.16.840.1.113883.3.1937.777.24.5.3.6` and check whether the resource date falls within its period.

<details>
<summary>Example patient — provision .6 period</summary>

```json
{
    "type": "permit",
    "period": {
        "start": "2024-02-15",
        "end": "2054-02-28"
    },
    "code": [
        {
            "coding": [
                {
                    "system": "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3",
                    "code": "2.16.840.1.113883.3.1937.777.24.5.3.6",
                    "display": "MDAT erheben"
                }
            ]
        }
    ]
}
```

</details>

**Result:** `2024-02-20` falls within the consent period `2024-02-15 – 2054-02-28` ✅


## If the date is outside the provision .6 period

Work through the following steps in order:

**1. Check for retrospective consent (`.45` / `.46`)**

If either provision is present, extend the effective start date back to `1900-01-01`, giving an effective period of `1900-01-01 – 2054-02-28`. Re-check the resource date against this extended period.

**2. Check for an overlapping Encounter**

If retrospective consent does not cover the date, check whether the patient had an encounter that overlaps the consent period — an overlapping encounter moves the effective start date forward to the encounter's start.

```
GET http://fhir-base-url/fhir/Encounter?patient=mii-exa-test-data-patient-9&_format=json&date=lt2054-02-28&date=gt2024-02-15
```

If a matching encounter is found, use its start date as the effective consent start and re-check.

**3. Multiple consents per patient**

If your site stores multiple Consent resources per patient, the above checks are not sufficient. You will need to reconstruct the effective period by combining all PERMIT and DENY provisions for the same provision code.

---

> ⚠️ **If you find that consent has not been correctly enforced, please contact the FDPG team.**
