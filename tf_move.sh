u#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <src_state_file> <dest_state_file> <resource_list_file>"
  exit 1
fi

# Assign arguments to variables
SRC_STATE_FILE=$1
DEST_STATE_FILE=$2
RESOURCE_LIST_FILE=$3

# Check if the source state file exists
if [ ! -f "$SRC_STATE_FILE" ]; then
  echo "Error: Source state file '$SRC_STATE_FILE' does not exist."
  exit 1
fi

# Check if the destination state file exists
if [ ! -f "$DEST_STATE_FILE" ]; then
  echo "Error: Destination state file '$DEST_STATE_FILE' does not exist."
  exit 1
fi

# Check if the resource list file exists
if [ ! -f "$RESOURCE_LIST_FILE" ]; then
  echo "Error: Resource list file '$RESOURCE_LIST_FILE' does not exist."
  exit 1
fi

# Iterate through each line in the resource list file
while IFS= read -r RESOURCE; do
  # Skip empty lines or lines starting with # (comments)
  if [[ -z "$RESOURCE" || "$RESOURCE" == \#* ]]; then
    continue
  fi

  # Execute the terraform mv command
  echo "Moving resource: $RESOURCE"
  terraform state mv -state-out="$DEST_STATE_FILE" -state="$SRC_STATE_FILE" "$RESOURCE" "$RESOURCE"

  # Check if the terraform command was successful
  if [ $? -ne 0 ]; then
    echo "Error: Failed to move resource '$RESOURCE'."
    exit 1
  fi

done < "$RESOURCE_LIST_FILE"

echo "All resources have been successfully moved."
exit 0

