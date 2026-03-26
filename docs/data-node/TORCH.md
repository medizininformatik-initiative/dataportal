# Data Extraction - TORCH

Transfer Of Resources in Clinical Healthcare or [TORCH](https://medizininformatik-initiative.github.io/torch/) supports extracting data from a FHIR server based on a [CRTDL](https://github.com/medizininformatik-initiative/clinical-resource-transfer-definition-language).



## Using TORCH

**aether (Recommended)**

To simplify the data extraction process we recommend the use of the *D*ata *U*se *P*roject (DUP) pipeline coordination tool [aether](aether.md).

The tool supports the whole DUP pipeline at the site and can connect to TORCH directly to execute a CRTDL based data extraction for a DUP.

**FHIR API**

TORCH has a FHIR API, described [here](https://medizininformatik-initiative.github.io/torch/api/api.html).


**Extraction Script**

To simplify the use of TORCH a script to trigger an extraction is provided [here](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/torch/execute-crtdl.sh).

The use of which is described [here](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/torch/README.md)

