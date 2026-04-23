#!/bin/bash -e

script_dir="$(dirname "$(readlink -f "$0")")"
base="http://localhost:8082/fhir"

upload_file() {
  local filename="$1"
  local base_url="$2"
  
  resource_type="$(jq -r .resourceType "$filename")"
  
  if [[ "$resource_type" =~ ValueSet|CodeSystem ]]; then
    url="$(jq -r .url "$filename")"
    if [[ "$url" =~ http://unitsofmeasure.org|http://snomed.info/sct|http://loinc.org|urn:ietf:bcp:13 ]]; then
      echo "Skip creating the code system or value set $url which is internal in Blaze"
    else
      echo "Upload $filename"
      curl -sf -H "Content-Type: application/fhir+json" -H "Prefer: return=minimal" -d @"$filename" "$base_url/$resource_type"
    fi
  fi
}

# Parse command line arguments
specific_files=()
while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--base)
      base="$2"
      shift 2
      ;;
    -f|--file)
      shift
      while [[ $# -gt 0 && ! "$1" =~ ^- ]]; do
        specific_files+=("$1")
        shift
      done
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-b|--base BASE_URL] [-f|--file FILE1 FILE2 ...]"
      exit 1
      ;;
  esac
done

# Upload specific files or all files
if [[ ${#specific_files[@]} -gt 0 ]]; then
  # Upload specific files
  echo "Uploading ${#specific_files[@]} specific file(s) to $base..."
  for file in "${specific_files[@]}"; do
    upload_file "$file" "$base"
  done
else
  # Upload all files
  echo "Uploading all resources from $script_dir/node_modules to $base..."
  
  # Process files in batches to avoid command line length issues
  find "$script_dir/node_modules" -name "*.json" \
    -and -not -name "package.json" \
    -and -not -name ".package-lock.json" \
    -and -not -name ".index.json" \
    -print0 | while IFS= read -r -d '' file; do
    upload_file "$file" "$base" &
    
    # Limit parallel jobs to 4
    while [[ $(jobs -r -p | wc -l) -ge 4 ]]; do
      sleep 0.1
    done
  done
  
  # Wait for remaining jobs to complete
  wait
fi

# Show summary
num_code_systems="$(curl -s "$base/metadata?mode=terminology" | jq -r '.codeSystem | length')"
echo
echo "Successfully uploaded CodeSystem and ValueSet resources with a total of $num_code_systems code systems available now."