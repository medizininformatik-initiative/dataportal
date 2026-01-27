#!/bin/bash

TORCH_BASE_URL=${TORCH_BASE_URL:-http://localhost:8086}
TORCH_USERNAME=${TORCH_USERNAME:-""}
TORCH_PASSWORD=${TORCH_PASSWORD:-""}
CURL_INSECURE=${CURL_INSECURE:-false}

DIR_QUERIES="queries"
# check if queries directory exists
if [ ! -d "$DIR_QUERIES" ]; then
  DIR_QUERIES=$(mktemp -d)
  printf "Created temporary queries directory: %s\n" "$DIR_QUERIES"
fi

# Parse arguments
while getopts "f:p:" opt; do
  case $opt in
    f) json_file="$OPTARG" ;;
    p) patient_ids="$OPTARG" ;;
    *) echo "Usage: $0 -f <json_file> [-p patient1,patient2,...]" >&2; exit 1 ;;
  esac
done

if [ -z "$json_file" ]; then
  echo "Missing required JSON file (-f)" >&2
  exit 1
fi

CURL_OPTIONS=""
if [ "$CURL_INSECURE" = "true" ]; then
    CURL_OPTIONS="-k"
fi

TORCH_AUTHORIZATION=$(printf "%s:%s" "$TORCH_USERNAME" "$TORCH_PASSWORD" | base64 -w0)

base64_encoded=$(base64 -w0 < "$json_file")

payload='{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "crtdl",
      "valueBase64Binary": "'"$base64_encoded"'"
    }'

IFS=',' read -r -a patients <<< "$patient_ids"
for pid in "${patients[@]}"; do
  payload="$payload,
    {
      \"name\": \"patient\",
      \"valueString\": \"${pid}\"
    }"
done

payload="$payload
  ]
}"

echo "$payload" > $DIR_QUERIES/temp-execute-crtdl.json

echo "lines in temp-execute-crtdl.json"
wc -l $DIR_QUERIES/temp-execute-crtdl.json

echo "TORCH_BASE_URL=$TORCH_BASE_URL"

response=$(curl -v --location -s -i $CURL_OPTIONS "${TORCH_BASE_URL}/fhir/\$extract-data" \
  --header 'Content-Type: application/fhir+json' \
  --header "Authorization: Basic ${TORCH_AUTHORIZATION}" \
  --data @$DIR_QUERIES/temp-execute-crtdl.json)

rm $DIR_QUERIES/temp-execute-crtdl.json

# Get content location
content_location=$(printf "%s" "$response" | grep -i 'Content-Location:' | awk '{print $2}' | tr -d '\r')

if [ -n "$content_location" ]; then
  printf "\nExtraction submitted, find your extraction under:\n\n%s\n\n" "$content_location"
  printf "response=$response"
else
  printf "Content-Location header not found in the response.\n"
  printf "Response received:\n%s\n" "$response"
fi
