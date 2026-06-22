# Additional information for the fhir-pseudonymizer

https://github.com/miracum/fhir-pseudonymizer 


This example uses the vfps as pseudonymization service, make sure to change it to your local pseudonymization service of choice.

It is important that the pseudonyms are kept save and persisted over a long period of time so that project based re-identification can be guranteed should the need arise.

## dimp_dup_base.yaml example and per project configuration

The `dimp_dup_base.yaml` of this project is an example and configures a base DIMP example, which has to be adjusted on a per project basis.

For each project unless otherwise specified the following need to be adjusted:

1. `parameters.cryptoHashKey` needs to be filled with a crypohashkey for the project. You can use the following command for this `openssl rand -hex 32`
2. The `project-prefix-here` part in the `dimp_dup_base.yaml` should be replaced with your project prefix.

Additionally projects can differ in other DIMP aspects, which will be provided as part of each projects DIMP specification - e.g. birtdate aggregated to year instead of year-month.


## Using the vfps

If a site is using the vfps of this example, the fhir-pseudonymizer needs the pseudonym domains used in the [dimp_dup_base.yaml](./dimp_dup_base.yaml) to exist in the vfps.

For testing purposes one can keep `my-dic-encounter-namespace` and `my-dic-patient-namespace`, otherwise change to your domain of choice.

To create the domains in the vfps use the following post requests:


```
curl --request POST \
  --url http://localhost:8089/v1/namespaces \
  --header 'content-type: application/json' \
  --data '{
  "name": "my-dic-patient-namespace",
  "pseudonymGenerationMethod": "PSEUDONYM_GENERATION_METHOD_UNSPECIFIED",
  "pseudonymLength": 32,
  "pseudonymPrefix": "string",
  "pseudonymSuffix": "string",
  "description": "string"
}'
```


```
curl --request POST \
  --url http://localhost:8089/v1/namespaces \
  --header 'content-type: application/json' \
  --data '{
  "name": "my-dic-encounter-namespace",
  "pseudonymGenerationMethod": "PSEUDONYM_GENERATION_METHOD_UNSPECIFIED",
  "pseudonymLength": 32,
  "pseudonymPrefix": "string",
  "pseudonymSuffix": "string",
  "description": "string"
}'
```