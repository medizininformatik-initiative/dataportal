# MII FHIR Flattener - Overview

Flattening is the act of transforming FHIR Data from an object format into a flattened format - typically csv or parquet.

To flatten data the fhir-flattener webservice is used, which based on the [pathling library](https://pathling.csiro.au/) takes a FHIR [viewDefinition](https://build.fhir.org/ig/FHIR/sql-on-fhir-v2/StructureDefinition-ViewDefinition.html)
and FHIR resources and flattens them.

## Use in the DUP pipeline

In the DUP pipelin the [aether](aether.md) takes the extracted resources and based on a CRTDL generates ViewDefinitions for the specific DUP using
a flatteningLookup table, which is provided as part of the [FDPG ontology](https://github.com/medizininformatik-initiative/fhir-ontology-generator).

The lookup table is still in development, but a first version can be downloaded from our [example deployment](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/aether/flatteningLookup.json) to try out the flattening
in conjunction with aether.

## The flattening ruels for the Core Data Set (CDS)

The flatteningLookup table is generated based on specific rules and the CDS profiles as described [here](https://github.com/medizininformatik-initiative/fhir-ontology-generator/blob/406-generate-fhir-flattening-viewdefintion-lookup-file/flattening/README.md).

## Use of the flattener without aether

The fhir-flattener can also be used without aether and the viewDefinition lookup table.
In this case the the users have to create their own view definition and use the [fhir-flattener api](https://github.com/medizininformatik-initiative/fhir-flattener) to flatten their resources.


