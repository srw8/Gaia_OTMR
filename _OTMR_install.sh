# This script should copy OTMR requirments from home to where they belong on instrument.
# copy recipe, input sheet, python scripts to where they need to be

#!/bin/bash

# Set variables
REPO_URL="https://github.com/srw8/Celeste_Top_Descriptor"
FILE_PATH="CelesteTopUT.flowcell"
OUTPUT_PATH=$(pwd)
BRANCH="main" # Default branch

# Check if branch is provided as an argument
if [ -n "$1" ]; then
    BRANCH="$1"
fi

# Fetch the specific file
git init temp_repo
cd temp_repo
git remote add origin "$REPO_URL"
git fetch origin "$BRANCH" --depth 1
git checkout "origin/$BRANCH" -- "$FILE_PATH"

# Copy the file to the desired output path
mkdir -p "$(dirname "$OUTPUT_PATH")" # Create the directory if it doesn't exist
cp "$FILE_PATH" "$OUTPUT_PATH"

# Clean up
cd ..
rm -rf temp_repo

echo "File '$FILE_PATH' from '$REPO_URL' (branch '$BRANCH') pulled successfully