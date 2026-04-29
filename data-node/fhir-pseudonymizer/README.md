# Additional information for the fhir-pseudonymizer

https://github.com/miracum/fhir-pseudonymizer 


This example uses the vfps as pseudonymization service, make sure to change it to your local pseudonymization service of choice.

It is important that the pseudonyms are kept save and persisted over a long period of time so that project based re-identification can be guranteed should the need arise.


## Using the vfps

If a site is using the vfps of this example, the fhir-pseudonymizer needs the pseudonym domains used in the [dimp_dup_base.yaml](./dimp_dup_base.yaml) to exist in the vfps.

For testing purposes one can keep `https://my-dic-domain/identifiers/encounter-id` and `https://my-dic-domain/identifiers/patient-id`, otherwise change to your domain of choice.

To create the domains in the vfps use the following post requests:


```
curl --request POST \
  --url http://localhost:8089/v1/namespaces \
  --header 'content-type: application/json' \
  --data '{
  "name": "https://my-dic-domain/identifiers/patient-id",
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
  "name": "https://my-dic-domain/identifiers/encounter-id",
  "pseudonymGenerationMethod": "PSEUDONYM_GENERATION_METHOD_UNSPECIFIED",
  "pseudonymLength": 32,
  "pseudonymPrefix": "string",
  "pseudonymSuffix": "string",
  "description": "string"
}'
```

