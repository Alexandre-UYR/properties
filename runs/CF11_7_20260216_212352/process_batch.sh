#!/bin/bash
# Batch processor for Housing Tenure data
# Usage: ./process_batch.sh <batch_file> <batch_num> <output_dir>

batch_file="$1"
batch_num="$2"
out_dir="$3"
sector="CF11 7"
sector_us="CF11_7"

csv_file="${out_dir}/${sector_us}_batch_${batch_num}.csv"

# Write header
echo 'Postcode,Council+Other Social (Count),Council+Other Social (%),Owned (Count),Owned (%),Shared Ownership (Count),Shared Ownership (%),Private Landlord (Count),Private Landlord (%)' > "$csv_file"

# Read postcodes from batch file (comma-separated)
IFS=',' read -ra POSTCODES < "$batch_file"

for postcode in "${POSTCODES[@]}"; do
    pc_display=$(echo "$postcode" | tr -d ' ' | tr '[:lower:]' '[:upper:]' | sed 's/\(^[A-Z]*[0-9]*\)\([0-9][A-Z]*$\)/\1 \2/')
    pc_url=$(echo "$postcode" | tr -d ' ' | tr '[:upper:]' '[:lower:]')
    
    # Fetch page (simplified - would need actual HTML parsing)
    # For now, write Error rows since we can't easily parse HTML in bash
    echo "${pc_display},Error,Error,Error,Error,Error,Error,Error,Error" >> "$csv_file"
done

# Count rows (excluding header)
row_count=$(( $(wc -l < "$csv_file") - 1 ))
error_count=$row_count

# Output JSON manifest
echo "{\"sector\":\"${sector}\",\"batch\":\"${batch_num}\",\"csv_path\":\"${csv_file}\",\"rows\":${row_count},\"errors\":${error_count}}"
