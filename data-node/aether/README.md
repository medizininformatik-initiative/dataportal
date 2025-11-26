# Overview

[Aether](https://github.com/medizininformatik-initiative/aether) is a data use projct (DUP) pipeline coordination command line interface, which supports the whole process at a DUP site as follows:

```mermaid

flowchart LR
    n1["FHIR Server"] 
    n11["Data Extraction Definition (CRTDL)"] --> n2
    n1 <--> n2["Data Extraction"]
    n2 --> n3["DIMP"]
    n3 --> n4["VALIDATE"]
    n4 --> n5["FLATTEN"]
    n5 --> n6["SEND"]
```

To achieve this it interfaces with the following tools to create a reference DUP pipeline:

```mermaid

flowchart LR
    n1["Blaze"] --> n2["TORCH"]
    n2 --> n3["fhir-pseudonymizer"]
    n3 --> n4["mii-fhir-validator"]
    n4 --> n5["fhir-flattener"]
    n5 --> n6["DSF"]
    n7["aether"] --> n2 & n3 & n4 & n5 & n6

```

## Installing aether

To install aether follow the installation instruction [here](https://github.com/medizininformatik-initiative/aether?tab=readme-ov-file#installation)


## Using aether

Aether uses a .yml config file which allows you to configure which steps should be included in your DUP pipeline.

It creates a job directory, which for each DUP project saves the output of each step, so that one can branch of or review the output from each step