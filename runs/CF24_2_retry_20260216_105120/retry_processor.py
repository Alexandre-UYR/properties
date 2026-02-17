#!/usr/bin/env python3
"""
Retry processor for CF24 2 postcodes that previously failed.
Fetches housing tenure data from StreetCheck and writes to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import sys

def normalize_postcode_for_url(postcode):
    """Convert 'CF24 2JY' to 'cf242jy'"""
    return postcode.replace(' ', '').lower()

def parse_housing_tenure(postcode):
    """Fetch and parse housing tenure data for a single postcode"""
    url_postcode = normalize_postcode_for_url(postcode)
    url = f"https://www.streetcheck.co.uk/postcode/{url_postcode}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the housing section
        housing_div = soup.find('div', id='housing')
        if not housing_div:
            return None

        # Find the Housing Tenure subsection
        tenure_heading = None
        for h3 in housing_div.find_all('h3'):
            if 'housing tenure' in h3.get_text().lower():
                tenure_heading = h3
                break

        if not tenure_heading:
            return None

        # Find the table following this heading
        table = tenure_heading.find_next('table')
        if not table:
            return None

        # Extract data from table
        data = {}
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text().strip()
                value_text = cells[1].get_text().strip()
                # Remove commas and convert to int
                try:
                    value = int(value_text.replace(',', ''))
                    data[label.lower()] = value
                except ValueError:
                    continue

        # Extract required fields
        result = {
            'council': data.get('rented: from council', 0),
            'other_social': data.get('rented: other social', 0),
            'owned_out': data.get('owned outright', 0),
            'owned_mort': data.get('owned with mortgage', 0),
            'shared': data.get('shared ownership', 0),
            'private': data.get('rented: private landlord inc. letting agents', 0),
            'total': data.get('total', 0)
        }

        if result['total'] == 0:
            return None

        return result

    except Exception as e:
        print(f"Error fetching {postcode}: {e}", file=sys.stderr)
        return None

def calculate_percentage(count, total):
    """Calculate percentage with 2 decimal places"""
    if total == 0:
        return "0.00%"
    return f"{(count / total * 100):.2f}%"

def process_postcodes(postcodes_file, output_csv):
    """Process all postcodes and write to CSV"""

    # Read postcodes
    with open(postcodes_file, 'r') as f:
        postcodes = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(postcodes)} postcodes...")

    # Open CSV for writing
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write header (EXACT schema required)
        writer.writerow([
            'Postcode',
            'Council+Other Social (Count)',
            'Council+Other Social (%)',
            'Owned (Count)',
            'Owned (%)',
            'Shared Ownership (Count)',
            'Shared Ownership (%)',
            'Private Landlord (Count)',
            'Private Landlord (%)'
        ])

        # Process each postcode
        success_count = 0
        error_count = 0

        for i, postcode in enumerate(postcodes, 1):
            print(f"Processing {i}/{len(postcodes)}: {postcode}...", file=sys.stderr)

            data = parse_housing_tenure(postcode)

            if data is None:
                # Write error row
                writer.writerow([postcode, 'Error', 'Error', 'Error', 'Error', 'Error', 'Error', 'Error', 'Error'])
                error_count += 1
            else:
                # Calculate derived values
                social_count = data['council'] + data['other_social']
                owned_count = data['owned_out'] + data['owned_mort']
                total = data['total']

                # Calculate percentages
                social_pct = calculate_percentage(social_count, total)
                owned_pct = calculate_percentage(owned_count, total)
                shared_pct = calculate_percentage(data['shared'], total)
                private_pct = calculate_percentage(data['private'], total)

                # Write row
                writer.writerow([
                    postcode,
                    social_count,
                    social_pct,
                    owned_count,
                    owned_pct,
                    data['shared'],
                    shared_pct,
                    data['private'],
                    private_pct
                ])
                success_count += 1

            # Rate limiting - be polite to the server
            time.sleep(0.5)

    print(f"\nComplete! Success: {success_count}, Errors: {error_count}")
    print(f"Output: {output_csv}")

if __name__ == '__main__':
    postcodes_file = '/home/alexandre/properties/runs/CF24_2_retry_20260216_105120/CF24_2_postcodes.txt'
    output_csv = '/home/alexandre/properties/runs/CF24_2_retry_20260216_105120/CF24_2_retry_Housing_Tenure_Summary.csv'

    process_postcodes(postcodes_file, output_csv)
