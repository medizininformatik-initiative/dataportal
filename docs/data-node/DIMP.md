# DIMP (De-Identification-Minimisation-Pseudonymisation)

DIMP is the act of 

- **De-identifying**: Aggregating or transforming data to prevent re-identification (e.g. cutting of the birthdate at the month, shortening the ZIP from 5 to 2 characters)
- **Minimizing**: Removing any data from a data set which is not necessary for a specific data use project (e.g. for a study which requires diagnosis codes the free text annotation of the diagnosis is not necessary)
- **Pseudonymising**: Replacing identifier or IDs with Pseudonyms or hashed IDs to avoid direct re-identification (e.g. Patiend-ID-123 -> Patient_PSEUDONYM-999)

data for a data use project to preserve patient privacy.


## FHIR Pseudonymizer and DIMP DUP Base yaml

To support standardized data use projects (DUPs), a DIMP DUP base configuration has been created, which can be used in conjunction with the [fhir-pseudonymizer](https://github.com/miracum/fhir-pseudonymizer) to apply DIMP functions to data. 
It implements the DIMP pseudonymization functions required by most data use projects for the fields defined in the MII core dataset.

This configuration is provided as a guideline only and does not guarantee compliance with applicable data privacy regulations.

Depending on your specific setup or the characteristics of your data, this base configuration 
will likely need to be extended or adjusted to meet the requirements of your particular project and/or site.

The base configuration is located at [data-node/aether/dimp_dup_base.yaml](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/aether/dimp_dup_base.yaml), next to the aether pipeline configuration, because it is sent to the `fhir-pseudonymizer` by aether per DUP project rather than being mounted into the container — see [Setup](#setup).

<details>
<summary>Table with list of applied DIMP rules: </summary>

| DSC Concept | FHIR Resource | FHIR Element | Privacy Requirement | Description | DIMP Implementation | DUP Base YAML |
|---|---|---|---|---|---|---|
| Technical ID | All | `.id` | Crypto hash | Technical resource ID, generated and assigned by the FHIR server. Not meaningful outside the system. | Replace with CryptoHash | `- path: Resource.id`<br>`  method: cryptoHash`<br>`  truncateToMaxLength: 32` |
| Technical References | All | `.reference` | Crypto hash | Technical reference IDs linking resources to one another. | Replace with CryptoHash | `- path: nodesByType('Reference').reference`<br>`  method: cryptoHash`<br>`  truncateToMaxLength: 32` |
| Reference Identifier | All | `Reference.identifier` | Redact unless explicitly kept — see Encounter and Patient identifier rules | Logical identifier embedded in a reference. The known CDS types (VN, MR) and the FDPG `attribute_group` and `extraction_id` namespaces are kept by dedicated rules; every other reference identifier is removed by the catch-all identifier rule at the end of the file. | Keep the listed types, redact the rest | `- path: nodesByType('Reference').identifier.where(type.coding.where(system='http://terminology.hl7.org/CodeSystem/v2-0203' and (code='VN')).exists())`<br>`  method: keep` |
| Encounter Identifier | All | `Encounter.identifier` | IDAT – do not export | Logical encounter identifier, potentially a direct reference to the hospital's internal encounter ID (e.g. VN). | Replace via re-pseudonymization using pseudonymization software | `- path: nodesByType('Identifier').where(type.coding.where(system='http://terminology.hl7.org/CodeSystem/v2-0203' and code='VN').exists()).value`<br>`  method: pseudonymize`<br>`  domain: https://my-dic-domain/identifiers/encounter-id` |
| Patient Identifier | All | `Patient.identifier` | IDAT – do not export | Logical patient identifier, potentially a direct reference to the hospital's internal patient ID (e.g. MR). | Replace via re-pseudonymization using pseudonymization software | `- path: nodesByType('Identifier').where(type.coding.where(system='http://terminology.hl7.org/CodeSystem/v2-0203' and code='MR').exists()).value`<br>`  method: pseudonymize`<br>`  domain: https://my-dic-domain/identifiers/patient-id` |
| Name | Patient | `Patient.name` | IDAT – do not export | Patient name; multiple `HumanName` elements may be present (e.g. official, maiden, nickname). | Redact all `HumanName` nodes | `- path: nodesByType('HumanName')`<br>`  method: redact` |
| Sex | Patient | `Patient.gender` | IDAT and MDAT – export permitted | Administrative gender per the FHIR required value set (male, female, other, unknown). | – | – |
| Date of Birth | Patient | `Patient.birthDate` | IDAT and MDAT – generalize to at least month precision | Full date of birth of the patient. Must be generalized before export. | Generalize to year-month (YYYY-MM) | `- path: Patient.birthDate`<br>`  method: generalize`<br>`  cases:`<br>`    "$this": "$this.toString().replaceMatches('(?<year>\\d{2,4})-(?<month>\\d{2})-(?<day>\\d{2})\\b', '${year}-${month}')"` |
| Deceased (flag) | Patient | `Patient.deceased.ofType(boolean)` | IDAT – removal recommended per DSC; subject to further discussion | Boolean flag indicating whether the patient is deceased (true/false). | Keep as-is | `- path: Patient.deceased.ofType(boolean)`<br>`  method: keep` |
| Deceased (date) | Patient | `Patient.deceased.ofType(dateTime)` | IDAT – removal recommended per DSC; subject to further discussion | Date and time of death. Could potentially be generalized to month precision analogous to date of birth — open for discussion. Redacted for now. | Redact | `- path: Patient.deceased.ofType(dateTime)`<br>`  method: redact` |
| Address | Patient | `Patient.address` | IDAT – remove | Full address information in any form (home, work, temp, etc.). | Redact all `Address` nodes | `- path: nodesByType('Address')`<br>`  method: redact` |
| Postal Code | Patient | `Patient.address.postalCode` | IDAT and MDAT – generalize to 2 digits | Postal code component of an address. Retaining the first 2 digits preserves regional granularity while reducing re-identification risk. | Generalize to first 2 characters | `- path: Patient.address.postalCode`<br>`  method: generalize`<br>`  cases:`<br>`    "$this": "$this.toString().substring(0,2)"` |
| Free Text | All | `nodesByType('Annotation')` | IDAT – remove | Unstructured free-text fields such as `Observation.note`. May contain patient-identifiable information and cannot be reliably de-identified automatically. | Redact | `- path: nodesByType('Annotation')`<br>`  method: redact` |
| Identifier Assigner | All | `Identifier.assigner` | Site identifying – remove | Reference to the organisation that issued the identifier. `assigner.display` carries the institution name in cleartext, and `assigner.reference` a technical id that the reference hashing does not reach once the identifier is kept. | Redact | `- path: nodesByType('Identifier').assigner`<br>`  method: redact` |
| Remaining Identifiers | All | `Identifier` | Remove unless explicitly kept | Any identifier not matched by a more specific rule above — site-local case numbers, lab accession numbers, specimen ids, identifiers whose `type.coding` a site does not populate. Removed whole, `system` and `value` together. | Redact | `- path: nodesByType('Identifier')`<br>`  method: redact` |

</details>

> [!IMPORTANT]
> **Rule order decides the outcome.** `fhirPathRules` is evaluated first-match-wins: the first rule that matches a node wins, and a rule matching a parent claims its whole subtree. Three consequences when you adapt the YAML:
>
> - The `keep` that follows each `pseudonymize` shields the rest of that identifier from the blanket rules further down. Keep each pair together and in that order.
> - Anything that must be stripped from an identifier that is later kept — `assigner`, for example — has to be stated **before** the `keep`, or it survives.
> - The catch-all identifier rule has to stay at the **end** of the file, after the insurance fail-safe. As long as it is `redact` the outcome is the same either way, but a project that switches it to the commented `cryptoHash` alternative and leaves it higher up would hash the insurance identifiers instead of deleting them.

---

### Using and Customizing the DUP YAML

The DUP base YAML file included in the repository is a starting point — not a final configuration. Each site or project needs to adapt it to meet their specific requirements.

#### Setup

The DIMP configuration is **not** mounted into the `fhir-pseudonymizer` container per project. Instead, aether sends the project's DIMP YAML to the `fhir-pseudonymizer` with every `$de-identify` request. Each pipeline run therefore uses exactly the YAML its pipeline configuration points at — no restart and no reconfiguration of the container between projects.

Two settings decide which rules are applied:

| Where | What | Purpose |
|---|---|---|
| aether pipeline config | `services.dimp.anonymization_config`, e.g. in [base-pipeline-config.yml](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/aether/base-pipeline-config.yml) | The DIMP YAML aether sends with each `$de-identify` request — this is the configuration that actually DIMPs your project's data. It overrides whatever the `fhir-pseudonymizer` is configured with. It can be overridden per run with `aether pipeline start <config> <crtdl> --anonymization-config <path>`. |
| fhir-pseudonymizer container | `DIMP_DUP_YAML_PATH` in `data-node/fhir-pseudonymizer/.env`, default [redact-all.yaml](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/fhir-pseudonymizer/redact-all.yaml) | The static fall-back configuration, used only for requests that arrive **without** a DIMP YAML. It redacts everything (`- path: Resource` / `method: redact`). |

> [!IMPORTANT]
> Keep `redact-all.yaml` as the mounted fall-back configuration. It ensures that a request which does not carry a project DIMP configuration — a misconfigured pipeline, a manual call, another client — returns an empty resource instead of un-DIMPed data. Replacing it with a real DIMP configuration re-introduces the risk of exporting data under the wrong project's rules.

> [!WARNING]
> Sending the configuration per request requires `fhir-pseudonymizer` >= `v2.34.0` (this repository pins `v3.1.2`) and aether >= `v1.4.0`. Earlier aether versions used `services.dimp.experimental_v3.anonymization_config`; that option has been removed — move the path up to `services.dimp.anonymization_config`.

---

#### Re-Pseudonymization in the CDS

Patients in the CDS may have multiple identifiers, each of which may need to be re-pseudonymized differently depending on your project's requirements. For each identifier type, your site should create a dedicated pseudonym namespace.

There are three ways to handle each identifier:

| Option | When to use |
|---|---|
| **Don't re-pseudonymize** | The identifier is already pseudonymized and no additional per-project pseudonymization is needed |
| **Re-pseudonymize for extraction** (shared namespace across projects) | The identifier is not yet pseudonymized, or your site requires pseudonymization for data extractions generally - note this is an uncommon use case |
| **Re-pseudonymize per DUP project** (separate namespace per project) | The identifier is not yet pseudonymized and your site requires a distinct pseudonym for each individual DUP project - The standard use case|

#### Identifier Reference Table

The CDS defines the following standard patient identifiers. Check which ones your site actually uses:

| Profile field (slice) | DIMP FHIR path |
|---|---|
| `Patient.identifier:pid` | `nodesByType('Identifier').where(type.coding.where(system='http://terminology.hl7.org/CodeSystem/v2-0203' and code='MR').exists()).value` |
| `Patient.identifier:PseudonymisierterIdentifier` | `nodesByType('Identifier').where(type.coding.where(system='http://terminology.hl7.org/CodeSystem/v3-ObservationValue' and code='PSEUDED').exists()).value` |
| `Patient.identifier:AnonymisierterIdentifier` | `nodesByType('Identifier').where(type.coding.where(system='http://terminology.hl7.org/CodeSystem/v3-ObservationValue' and code='ANONYED').exists()).value` |

> **Always redacted:** `Patient.identifier:versichertenId` and `Patient.identifier:MaskierterVersichertenIdentifier` are always removed using the FHIR path:
> `nodesByType('Identifier').where(type.coding.where(system='http://fhir.de/CodeSystem/identifier-type-de-basis' and (code='GKV' or code='PKV' or code='KVZ10')).exists())`

> **Site-specific identifiers:** Any additional identifiers your site has added that are not defined as a slice in the CDS profile must be removed during the DIMP process. This is your site's responsibility.


#### The standard DIMP use case - per project DIMP

The standard use case for a DUP is to re-pseudonymize using project specific namespaces and cryptohashing of IDs for the specific project (new hash key per project).

For each project, unless otherwise specified, the following need to be adjusted:

1. `parameters.cryptoHashKey` needs to be filled with a crypohashkey for the project. You can use the following command for this `openssl rand -hex 32` to generate a new key for your project
2. The `project-prefix-here` part in [dimp_dup_base.yaml](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/aether/dimp_dup_base.yaml) should be replaced with your project prefix.

The best way to achieve the DUP based DIMP is to copy the base YAML to a project specific file (e.g. `project-prefix-dimp-dup-base.yaml`), keep it next to the project's aether pipeline configuration and point `services.dimp.anonymization_config` at it.
Because the YAML travels with each request, one `fhir-pseudonymizer` instance can serve several projects — the project's pipeline configuration, not the running container, decides which rules are applied, so there is no need to restart or shut down the pseudonymizer between projects.

See [data-node/example-dup-project](https://github.com/medizininformatik-initiative/dataportal/tree/main/data-node/example-dup-project) for a complete, runnable example of such a project setup.


#### Configuration Checklist - standard DUP project

1. Identify which patient identifiers your site uses
2. Save the DUP YAML with your project prefix and update it to reflect the correct re-pseudonymization for each identifier, create a new cryptohash key for your project and set it as `parameters.cryptoHashKey`
3. Point `services.dimp.anonymization_config` in your project's aether pipeline configuration at that file (the path is resolved relative to the pipeline configuration), or pass it per run with `aether pipeline start <config> <crtdl> --anonymization-config <path>`
4. Create the needed namespaces in your pseudonymization service (e.g. vfps, gPas, Enticy) **before** running the DIMP step — if a namespace is missing, the `fhir-pseudonymizer` will fail and break the pipeline - (For instructions on creating namespaces in vfps, see [this guide](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/fhir-pseudonymizer/README.md))
5. Check that your DUP configuration is really the one being applied by sending a pseudonymization query with your project YAML as shown below, and check that the hashed id of the resource equals the first 32 digits of `echo -n "VHF02002-CD-1" | openssl dgst -sha256 -hmac "<YOUR_KEY>"`. No restart of the `fhir-pseudonymizer` is needed — the configuration is read from the request
6. Check that the `fhir-pseudonymizer` still has `redact-all.yaml` mounted as its fall-back configuration, so that a run without a project configuration cannot produce un-DIMPed data
7. It is important that you ensure that the pseudonymization service you use is persisted at your site as this is the only option to re-identify patients later should this be necessary.




<details>
<summary>Example curl requests to check your DIMP configuration </summary>

**1. Check the fall-back configuration**

A plain `$de-identify` request carries no DIMP configuration, so the `fhir-pseudonymizer` falls back to its mounted configuration:

```bash
curl --request POST \
  --url 'http://localhost:8083/fhir/$de-identify' \
  --header 'content-type: application/fhir+json' \
  --data '{
  "resourceType": "Condition",
  "id": "VHF02002-CD-1",
  "meta": {
    "profile": [
      "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
    ]
  },
  "code": {
    "coding": [
      {
        "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
        "version": "2020",
        "code": "I95.0"
      }
    ],
    "text": "Idiopathische Hypotonie"
  },
  "subject": {
    "reference": "Patient/VHF02002"
  },
  "recordedDate": "2021-01-01T00:00:00+01:00"
}'
```

With `redact-all.yaml` mounted, everything is removed — this is the expected response:

```json
{"resourceType":"Condition","meta":{"security":[{"system":"http://terminology.hl7.org/CodeSystem/v3-ObservationValue","code":"REDACTED","display":"redacted"}]}}
```

**2. Check your project DIMP configuration**

To check the rules that are actually applied to your project's data, send the YAML with the request the way aether does — as a base64 encoded `config` attachment next to the `resource` in a `Parameters` resource:

```bash
CONFIG_B64=$(base64 < ./example-project_dimp_dup_base.yaml | tr -d '\n')

curl --request POST \
  --url 'http://localhost:8083/fhir/$de-identify' \
  --header 'content-type: application/fhir+json' \
  --data @- <<EOF
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "config",
      "valueAttachment": {
        "contentType": "application/yaml",
        "data": "$CONFIG_B64"
      }
    },
    {
      "name": "resource",
      "resource": {
        "resourceType": "Condition",
        "id": "VHF02002-CD-1",
        "meta": {
          "profile": [
            "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
          ]
        },
        "code": {
          "coding": [
            {
              "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
              "version": "2020",
              "code": "I95.0"
            }
          ],
          "text": "Idiopathische Hypotonie"
        },
        "subject": {
          "reference": "Patient/VHF02002"
        },
        "recordedDate": "2021-01-01T00:00:00+01:00"
      }
    }
  ]
}
EOF
```

The returned `Condition.id` is the first 32 characters of the HMAC of the original id under your project's `parameters.cryptoHashKey`. With the example project's key:

```bash
echo -n "VHF02002-CD-1" | openssl dgst -sha256 -hmac "d5c00fe954186e0f2da921cbecfb5765df115ea236188aee0cb020e50be2c89d"
# SHA2-256(stdin)= 6266e55af1ac4d2f474a543afe795e95da201cc0626c6ac1c608874d377bc4ea
#                  |---- returned Condition.id ---|
```

</details>

### Working with DIMPED data and re-identification

Once data is DIMPed for a DUP the data set does not contain any original technical IDs or identifier anymore.
Therefore additional steps are required for debugging and checking correct data extraction (like consent compliance).

> [!INFO]
> The technical id - ID - is a technical identifier used in the FHIR server to identify a data entry and has no direct correspondance to the primary data in the hospital, this ID does not contain sensitive information and is commonly generated on load into the FHIR server (It is each sites responsibility to assess wether cryptohashing their technical IDs is sufficient). This ID should not be confused with a logical Identifier for the patient like the medical record number (MR). Identifier can be used to re-identify a patient in the hospital. They have to be added to DUP data sets for re-identification purposes, for example in case of withdrawal (German = "Widerruf").


Given any data set in DIMPed fhir or CSV format (aether job step folders `dimp` and `csv`), the technical IDs cannot be reversed, however if you are looking for a particular ID in your final data set from your original you can use the following command:

```bash
echo -n "<ORIGINAL_ID>" | openssl dgst -sha256 -hmac "<YOUR_KEY>"
```

The key is the `parameters.cryptoHashKey` of the DIMP YAML the project was run with — which is why each project has to generate its own key and keep it.

> [!WARNING]
> `Anonymization__CryptoHashKey` in `data-node/fhir-pseudonymizer/.env` sets one key for the whole container, and `initialise-node-env-files.sh` generates and fills it on first setup — so it is **not** empty on a fresh node. If a project's DUP YAML leaves `parameters.cryptoHashKey` unset, the container key is used silently: no error, no warning, and output that looks correct, with every project sharing one key. Step 5 of the checklist above is what catches this — the returned id will not match the HMAC computed under your project key.

For the re-pseudonymized identifier you will have to use your specific pseudonymisation service to re-identify an identifier.

For vfps this is the following call:

```curl
curl --request GET \
  --url http://localhost:8089/v1/namespaces/my-namespace/pseudonyms/my-identifier \
  --header 'content-type: application/json'

e.g. 

curl --request GET \
  --url http://localhost:8089/v1/namespaces/my-dic-patient-namespace/pseudonyms/stringmlBC83Vba42cr4r8TkNMf65UNP9b3LNAIxfo0zKzk2NQp1IjT-a7ywstring \
  --header 'content-type: application/json'
  ```
