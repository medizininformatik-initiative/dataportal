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

<details>
<summary>Table with list of applied DIMP rules: </summary>

| DSC Concept | FHIR Resource | FHIR Element | Privacy Requirement | Description | DIMP Implementation | DUP Base YAML |
|---|---|---|---|---|---|---|
| Technical ID | All | `.id` | Crypto hash | Technical resource ID, generated and assigned by the FHIR server. Not meaningful outside the system. | Replace with CryptoHash | `- path: Resource.id`<br>`  method: cryptoHash`<br>`  truncateToMaxLength: 32` |
| Technical References | All | `.reference` | Crypto hash | Technical reference IDs linking resources to one another. | Replace with CryptoHash | `- path: nodesByType('Reference').reference`<br>`  method: cryptoHash`<br>`  truncateToMaxLength: 32` |
| Reference Identifier | All | `Reference.identifier` | Redact unless otherwise specified — see Encounter and Patient identifier rules | Logical identifier embedded in a reference. Redacted by default; specific identifier types are handled by more targeted rules below. | Redact | `- path: nodesByType('Reference').identifier`<br>`  method: redact` |
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

</details>

---

### Using and Customizing the DUP YAML

The DUP base YAML file included in the repository is a starting point — not a final configuration. Each site or project needs to adapt it to meet their specific requirements.

#### Setup

The DIMP configuration must be mounted into the `fhir-pseudonymizer` container at startup. See [this example](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/fhir-pseudonymizer/docker-compose.yml#L19) for how to do this. After changing the mounted file, restart the `fhir-pseudonymizer` for the changes to take effect.

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
2. The `project-prefix-here` part in the `dimp_dup_base.yaml` should be replaced with your project prefix.

The best way to achieve the DUP based DIMP is to create a project-prefix-dimp-dup-base.yml and mount this yaml to the pseudonymizer and restart it.
Once the project has been executed shut down the pseudonymizer and prepare for the next project.


#### Configuration Checklist - standard DUP project

1. Identify which patient identifiers your site uses
2. Update your DUP YAML to reflect the correct re-pseudonymization for each and create a new cryptohash key for your project and update it in the dup yaml
3. Save the DUP YAML with your project prefix and mount it into the fhir pseudonymizer. You can use the `DIMP_DUP_YAML_PATH` env variable in `data-node/fhir-pseudonymizer/.env` for this
3. Create the needed namespaces in your pseudonymization service (e.g. vfps, gPas, Enticy) **before** running the DIMP step — if a namespace is missing, the `fhir-pseudonymizer` will fail and break the pipeline - (For instructions on creating namespaces in vfps, see [this guide](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/fhir-pseudonymizer/README.md))
4. Restart the fhir-pseudonymizer and check if your DUP configuration has been updated. To check your configuration has been updated send a pseudonymization query as follows and check if the hashed id of the resource is equaled to the first 32 digits of `echo -n "VHF02002-CD-1" | openssl dgst -sha256 -hmac "<YOUR_KEY>"`
5. It is important that you ensure that the pseudonymization service you use is persisted at your site as this is the only option to re-identify patients later should this be necessary.




<details>
<summary>Example curl request to check pseudonymization configuration </summary>

```curl
curl --request POST \
  --url 'http://localhost:8083/fhir/$de-identify' \
  --header 'content-type: application/json' \
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

The key is configured as part of the pseudonymizer via the env variable `Anonymization__CryptoHashKey`.

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
