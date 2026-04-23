# The DUP Pipeline Overview

## Abstract DUP Pipeline

The DUP pipeline on an abstract level connects the following steps and services:

```mermaid

flowchart LR
    n1["FHIR Server"] 
    n1 --> n2["EXTRACT DATA"]
    n2 --> n3["DIMP"]
    n3 --> n4["VALIDATE"]
    n4 --> n5["FLATTEN"]
    n5 --> n6["SEND"]
    n7["DUP Pipeline Coordinator"] --- n2 & n3 & n4 & n5 & n6
```

## Reference DUP Pipeline

Translated to the reference software provided the piepline looks as follows:
```mermaid

flowchart LR
    n1["Blaze"] --> n2["TORCH"]
    n2 --> n3["fhir-pseudonymizer"]
    n3 --> n4["mii-fhir-validator"]
    n4 --> n5["fhir-flattener"]
    n5 --> n6["DSF"]
    n7["aether"] --- n2 & n3 & n4 & n5 & n6

```

## The DUP Reference Pipeline Detailed

Zooming in the more detailed pipeline can be depicted as follows:

```mermaid
flowchart LR
    n1["Blaze"] --> n2["TORCH"] & n3["FHIR Bundles"]
    n2 --> n3
    n3 --> n4["FHIR Bundles"] & n5["fhir-pseudonymizer"]
    n5 --> n4
    n4 --> n6["FHIR Bundles"] & n7["mii-fhir-validator"]
    n7 --> n6
    n6 --> n9["fhir-flattener"] & n11["DSF"] & n12["local DUP Fhir Server"] & n13["Local File system"]
    n9 --> n10["CSV or Parquet"]
    n10 --> n11 & n12 & n13
    n14["CRTDL"] --> n2
    n15["dup-dimp.yml"] --- n5
    n16["DUP ViewDefinitions"] --> n9
    n17["Aether"] --> n14 & n16
    n18["CRTDL"] --> n17
    n19["pipeline-config.yml"] --> n17
    n20["flatteing-lookup.config"] --- n17

    n3@{ shape: docs}
    n4@{ shape: docs}
    n6@{ shape: docs}
    n10@{ shape: docs}
    n14@{ shape: doc}
    n15@{ shape: doc}
    n16@{ shape: docs}
    n17@{ shape: rect}
    n18@{ shape: doc}
    n19@{ shape: doc}
    n20@{ shape: doc}
```