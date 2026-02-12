# The Fhir-Data-Evaluator (FDE)

The FDE is used as part of the data node to collect metadata about data available on the nodes FHIR server.
This aggregated metadat can then be sent via the DSF to the central portal or loaded into the local portal to display the availability
of single criteria in the fhir server and provide information about the completeness of the cds data.


## Configuration

For the general configuration of the FDE and an overview of the environment variables which can be set see: [fhir-data-evaluator](https://github.com/medizininformatik-initiative/fhir-data-evaluator)


## Running the FDE to provide the FDPG criteria availability and element availability reports

Run the FDE by executing the `run-fde` script provided [here](https://github.com/medizininformatik-initiative/dataportal/blob/main/data-node/fhir-data-evaluator/run-fde.sh).

The script and therefore the FDE has to be run for two different reports, by changing the environment variable `FDE_REPORT_TYPE` as follows before executing the `run-fde.sh` script:

1. `export FDE_REPORT_TYPE=cdsCodingAvailability`
2. `export FDE_REPORT_TYPE=DseElementAvailability`

You can, as is configured by default, send the metadata report back to your FHIR server which contains your patient data
or alternatively send the data to a different fhir server. The metadata report is sent in the form of a FHIR resource of
type `MeasureReport` along with a `DocumentReference` FHIR resource.

Regardless of the choice, the FHIR server which contains the report should be accessible from your DSE BPE in order to 
send the report to the central FDPG DSF using the [data transfer plugin][data-transfer].

The FDE creates a `MeasureReport` with respective `DocumentReference` on the target FHIR server - see `FHIR_REPORT_SERVER`env variable  in the [configuration options](https://github.com/medizininformatik-initiative/fhir-data-evaluator?tab=readme-ov-file#environment-variables).


## Sending the report to the central portal

> ⚠️ Only the DocumentReferences with the project identifiers `fdpg-data-availability-report-obfuscated` and `fdpg-data-element-availability-report-obfuscated` should be send to the FDPG.

If you want to send the report to the central portal, you need to install and configure the data transfer plugin in your
DSE BPE according to the [data transfer plugin documentation][data-transfer-doc]. Then you follow the steps mentioned in
the documentation's section [DIC: Start Send Process][start-send-process] to send the report to the central portal. 

Use the same project identifiers as configured in the run-fde.sh (`fdpg-data-availability-report-obfuscated` and `fdpg-data-element-availability-report-obfuscated`) by default and replace the DMS
organization identifier placeholder with the FDPG organization identifier `forschen-fuer-gesundheit.de`.


## Setting up a recurring send process

Once FDPG confirms successful report transfer from the initial run:
- Set up a scheduled job to run FDE for both report types sequentially (FDE is resource-intensive)
- Configure adequate delay between FDE completion and DSF transmission to ensure DocumentReference and MeasureReport resources are fully uploaded to your FHIR server before the data tranfser process is started.


[data-transfer]:  https://github.com/medizininformatik-initiative/mii-process-data-transfer
[data-transfer-doc]:  https://github.com/medizininformatik-initiative/mii-process-data-transfer/wiki
[start-send-process]: https://github.com/medizininformatik-initiative/mii-process-data-transfer/wiki/Process-Data-Transfer-Start-v1.0.x.x#dic-start-send-process
