# DIMP (De-Identification-Minimisation-Pseudonymisation)

DIMP is the act of 

- **De-identifying**: Aggregating or transforming data to prevent re-identification (e.g. cutting of the birthdate at the month, shortening the ZIP from 5 to 2 characters)
- **Minimizing**: Removing any data from a data set which is not necessary for a specific data use project (e.g. for a study which requires diagnosis codes the free text annotation of the diagnosis is not necessary)
- **Pseudonymising**: Replacing identifier or IDs with Pseudonyms or hashed IDs to avoid direct re-identification (e.g. Patiend-ID-123 -> Patient_PSEUDONYM-999)

data for a data use project to preserve patient privacy.

## FHIR Pseudonymizer and DIMP DUP Base yaml

To support standardized data use projects (DUPs), a DIMP DUP base configuration has been created, which can be used in conjunction with the [fhir-pseudonymizer](https://github.com/miracum/fhir-pseudonymizer) to apply DIMP functions to data. 
It implements the DIMP pseudonymization functions required by most data use projects for the fields defined in the MII core dataset.

This configuration is provided as a guideline only and does not guarantee compliance with 
applicable data privacy regulations.

Depending on your specific setup or the characteristics of your data, this base configuration 
will likely need to be extended or adjusted to meet the requirements of your particular project.


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

