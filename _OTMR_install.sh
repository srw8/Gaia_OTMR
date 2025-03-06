# This script should copy OTMR requirments from home to where they belong on instrument.
# copy recipe, input sheet, python scripts to where they need to be

#!/bin/bash

# Source and destination paths
SOURCE_FILE="/path/to/source/file"
DEST_FILE="/path/to/destination/file"

# Check if the destination file exists
if [ ! -f "$DEST_FILE" ]; then
    echo "File does not exist at $DEST_FILE. Copying from $SOURCE_FILE..."
    #cp "$SOURCE_FILE" "$DEST_FILE"
    #echo "File copied successfully."
else
    echo "File already exists at $DEST_FILE."
fi