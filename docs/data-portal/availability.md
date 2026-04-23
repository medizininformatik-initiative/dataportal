# FDPG Data Portal Availability

The data portal can display the availability of each criterion, if the availability is calculated and updated accordingly.

To load the availability into the dataportal requires the metadata information for the portal in the form of a MeasureReport which can be created using the fhir-data-evaluator.

We then provide an availability-updater, which downloads a new ontology version and your MeasureReport and based on this input calculates the availability for your data portal and uploads it
into your local elastic search as availability updates based on the context termcode hash (a hash used to uniquely identify each criterion).


## Data Portal Availability - How it Works

The data portal availability for each criterion is calculated using the FDE and an availability measure input provided as part of the data portal ontology.
The availability for each criterion is always calculated on patient level (e.g. If a patient has been diagnosed with Diabetes (E13 ICD10) twice its counted as 1).

The availability updater calculates the availability for parent concepts based on their children -> if there are 10 patients with E13.0 ICD10 and 5 with E13.1 ICD10 - E13 = 15.

Additionally, the updater sorts patient counts into buckets = (0, 10, 100, 1_000, 10_000, 100_000, 1_000_000) and loads it into the elastic search of the portal.

The portal then displays the buckets in the following mapping to the end user:

'unknown'. -> UNKNOWN = 0
'low' -> VERY LOW. = 10
'moderate' -> LOW. = 100
'medium' -> MEDIUM. = 1000
'high' -> HIGH. = 10_000
'full' -> VERY HIGH = 100_000 or 1_000_000


## Generating the local availability Report

Your local availability report can be generated using the [FDE](../data-node/fhir-data-evaluator.md) installed as part of you data node.

ToFollow the instruction [here](../data-node/fhir-data-evaluator.md) and generate the `cdsCodingAvailability` report.

This should lead to a `DocumentReference` and `MeasureReport` being created on your FHIR report server (this can be your fhir data server or an extra FHIR server only for the reports).

(It is important, that the availability-updater can access this server, so that it can download the report and load it into your local data portal).

To check if your report was successfully uploaded look for it via FHIR search as follows:

`curl http://<report-fhir-base-url>/fhir/DocumentReference?_format=json&identifier=http://medizininformatik-initiative.de/sid/project-identifier|fdpg-data-availability-report`

Note that for your local deployment you can use the unobfuscated report.


## Loading the availability into your data portal

To load the availability into your data portal you can use the [availability-updater](https://github.com/medizininformatik-initiative/availibility-updater) provided.

The updater is provided as a container image, but like the FDE is not a service but a container that runs and once finishes exits automatically.

To run it as part of the data portal see the script provided [here](https://github.com/medizininformatik-initiative/dataportal/tree/main/data-portal/availability-updater).



