#!/bin/bash
# Worker script to process one postcode and return CSV row
postcode="$1"
pc_display=$(echo "$postcode" | tr '[:lower:]' '[:upper:]')
pc_url=$(echo "$postcode" | tr -d ' ' | tr '[:upper:]' '[:lower:]')

# Fetch and extract - this is a stub, actual extraction would need proper HTML parsing
# For now, output Error row
echo "$pc_display,Error,Error,Error,Error,Error,Error,Error,Error"
