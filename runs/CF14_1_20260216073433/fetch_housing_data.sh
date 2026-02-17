#!/bin/bash
# Fetch housing tenure data for CF14 1 postcodes

INPUT_FILE="/home/alexandre/properties/runs/CF14_1_20260216073433/CF14_1_postcodes.txt"
OUTPUT_CSV="/home/alexandre/properties/runs/CF14_1_20260216073433/CF14_1_Housing_Tenure_Summary.csv"

# Write CSV header
echo "Postcode,Owned Outright,Owned with Mortgage,Shared Ownership,Rented: From Council,Rented: Other Social,Rented: Private Landlord,Rented: Other,Rent Free,Total,Social Housing Count,Social Housing %" > "$OUTPUT_CSV"

# Process each postcode
while IFS= read -r postcode; do
    # Normalize for URL (remove spaces, lowercase)
    url_code=$(echo "$postcode" | tr -d ' ' | tr '[:upper:]' '[:lower:]')

    # Fetch and parse the data using curl and basic text processing
    # This is a placeholder - actual implementation would need proper HTML parsing
    echo "Processing $postcode..." >&2

    # For now, write placeholder data
    echo "$postcode,Error,Error,Error,Error,Error,Error,Error,Error,Error,Error,Error" >> "$OUTPUT_CSV"

done < "$INPUT_FILE"

echo "Complete. Output saved to: $OUTPUT_CSV"
