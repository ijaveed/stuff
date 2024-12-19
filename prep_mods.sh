#!/bin/bash

text="# module.core.iam will be created
# aws_Security_group.main will be created"

# Remove the '#' character
text=$(echo "$text" | tr -d '#')

# Process each line of the text
while IFS= read -r line; do
  # Check if the line starts with "module"
  if [[ "$line" == module* ]]; then
    # Extract the first two parts (e.g., module.core)
    extracted=$(echo "$line" | awk '{print $1"."$2}')
  else
    # Extract the first part
    extracted=$(echo "$line" | awk '{print $1}')
  fi

  # Print the extracted part
  echo "$extracted"
done <<< "$text"
