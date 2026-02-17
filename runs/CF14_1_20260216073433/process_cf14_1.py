#!/usr/bin/env python3
"""
Process housing tenure data for CF14 1 postcodes.
Fetches data from StreetCheck and creates summary CSV.
"""

import urllib.request
import urllib.error
import re
import csv
import time
import sys
from pathlib import Path

def fetch_housing_data(postcode):
    """Fetch housing tenure data for a postcode from StreetCheck."""
    # Normalize for URL
    url_code = postcode.replace(' ', '').lower()
    url = f"https://www.streetcheck.co.uk/postcode/{url_code}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        # Find Housing Tenure section - look for the div containing housing data
        tenure_match = re.search(r'<h3[^>]*>Housing Tenure.*?</h3>(.*?)(?=<h3|<div class="section-break"|<footer|$)', html, re.DOTALL | re.IGNORECASE)
        if not tenure_match:
            return None, "Housing Tenure section not found"

        tenure_section = tenure_match.group(1)

        # Extract key-value pairs from the section
        # Look for patterns like "Label\n\nValue" or within table structure
        data = {}

        # Try to find table first
        if '<table' in tenure_section:
            tr_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows = re.findall(tr_pattern, tenure_section, re.DOTALL)

            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 2:
                    label = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    value_text = re.sub(r'<[^>]+>', '', cells[1]).strip().replace(',', '')
                    try:
                        value = int(value_text)
                        data[label] = value
                    except ValueError:
                        continue
        else:
            # Alternative format - extract from text content
            # Remove HTML tags but keep structure
            text_content = re.sub(r'<(?!br)([^>]+)>', '', tenure_section)
            text_content = re.sub(r'<br\s*/?>', '\n', text_content)

            # Look for known labels followed by numbers
            labels = [
                'Owned Outright',
                'Owned with Mortgage',
                'Shared Ownership',
                'Rented: From Council',
                'Rented: Other Social',
                'Rented: Private Landlord inc. letting agents',
                'Rented: Other',
                'Rent Free',
                'Total'
            ]

            for label in labels:
                # Look for label followed by a number
                pattern = rf'{re.escape(label)}\s*\n*\s*(\d+)'
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    data[label] = int(match.group(1))

        # Map to expected categories with flexible matching
        result = {
            'Owned Outright': data.get('Owned Outright', 0),
            'Owned with Mortgage': data.get('Owned with Mortgage or Loan', data.get('Owned with Mortgage', 0)),
            'Shared Ownership': data.get('Shared Ownership', 0),
            'Rented: From Council': data.get('Rented: From Council', 0),
            'Rented: Other Social': data.get('Rented: Other Social Rented', data.get('Rented: Other Social', 0)),
            'Rented: Private Landlord': data.get('Rented: Private Landlord or Letting Agency', data.get('Rented: Private Landlord', 0)),
            'Rented: Other': data.get('Rented: Other Private Rented', data.get('Rented: Other', 0)),
            'Rent Free': data.get('Living Rent Free', data.get('Rent Free', 0)),
            'Total': data.get('Total', 0)
        }

        if result['Total'] == 0:
            return None, "Total is zero or missing"

        # Calculate social housing
        social_count = result['Rented: From Council'] + result['Rented: Other Social']
        social_pct = (social_count / result['Total']) * 100 if result['Total'] > 0 else 0

        result['Social Housing Count'] = social_count
        result['Social Housing %'] = round(social_pct, 2)

        return result, None

    except urllib.error.URLError as e:
        return None, f"Request failed: {str(e)}"
    except Exception as e:
        return None, f"Error: {str(e)}"

def main():
    run_dir = Path("/home/alexandre/properties/runs/CF14_1_20260216073433")
    input_file = run_dir / "CF14_1_postcodes.txt"
    output_file = run_dir / "CF14_1_Housing_Tenure_Summary.csv"

    # Read postcodes
    with open(input_file, 'r') as f:
        postcodes = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(postcodes)} postcodes...")

    # CSV header
    fieldnames = [
        'Postcode', 'Owned Outright', 'Owned with Mortgage', 'Shared Ownership',
        'Rented: From Council', 'Rented: Other Social', 'Rented: Private Landlord',
        'Rented: Other', 'Rent Free', 'Total', 'Social Housing Count', 'Social Housing %'
    ]

    results = []
    errors = []

    for i, postcode in enumerate(postcodes, 1):
        print(f"[{i}/{len(postcodes)}] Fetching {postcode}...", end=' ')
        sys.stdout.flush()

        data, error = fetch_housing_data(postcode)

        if error:
            print(f"ERROR: {error}")
            errors.append((postcode, error))
            # Write error row
            results.append({
                'Postcode': postcode,
                'Owned Outright': 'Error',
                'Owned with Mortgage': 'Error',
                'Shared Ownership': 'Error',
                'Rented: From Council': 'Error',
                'Rented: Other Social': 'Error',
                'Rented: Private Landlord': 'Error',
                'Rented: Other': 'Error',
                'Rent Free': 'Error',
                'Total': 'Error',
                'Social Housing Count': 'Error',
                'Social Housing %': 'Error'
            })
        else:
            print(f"OK (Social: {data['Social Housing %']}%)")
            row = {'Postcode': postcode}
            row.update(data)
            results.append(row)

        # Rate limiting
        time.sleep(0.5)

    # Write CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Sort by social housing % (put errors at end)
        valid_rows = [r for r in results if r['Social Housing %'] != 'Error']
        error_rows = [r for r in results if r['Social Housing %'] == 'Error']

        valid_rows.sort(key=lambda x: x['Social Housing %'], reverse=True)

        for row in valid_rows + error_rows:
            writer.writerow(row)

    print(f"\nComplete!")
    print(f"Total postcodes: {len(postcodes)}")
    print(f"Successful: {len(postcodes) - len(errors)}")
    print(f"Errors: {len(errors)}")
    print(f"\nOutput saved to: {output_file}")

if __name__ == '__main__':
    main()
