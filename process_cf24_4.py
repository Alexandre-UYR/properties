#!/usr/bin/env python3
"""Process CF24 4 sector postcodes for social housing data."""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from pathlib import Path

def normalize_postcode_url(postcode):
    """Convert postcode to URL format: lowercase, no spaces."""
    return postcode.replace(' ', '').lower()

def extract_housing_tenure(postcode):
    """Fetch and extract housing tenure data for a postcode."""
    url_postcode = normalize_postcode_url(postcode)
    url = f"https://www.streetcheck.co.uk/postcode/{url_postcode}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find Housing Tenure section
        tenure_section = None
        for h3 in soup.find_all('h3'):
            if 'housing tenure' in h3.get_text().lower():
                tenure_section = h3.find_next('table')
                break

        if not tenure_section:
            return {'error': 'Housing Tenure section not found'}

        # Extract data from table
        data = {}
        rows = tenure_section.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text().strip()
                value_text = cells[1].get_text().strip()
                # Remove commas and extract number
                value_match = re.search(r'([\d,]+)', value_text)
                if value_match:
                    value = int(value_match.group(1).replace(',', ''))
                    data[label] = value

        # Extract required fields
        result = {
            'postcode': postcode,
            'council': data.get('Rented: From Council', 0),
            'other_social': data.get('Rented: Other Social', 0),
            'total': data.get('Total', 0)
        }

        if result['total'] == 0:
            return {'error': 'Total is zero or missing'}

        # Calculate social housing
        social_count = result['council'] + result['other_social']
        social_pct = (social_count / result['total']) * 100

        result['social_count'] = social_count
        result['social_pct'] = round(social_pct, 2)

        return result

    except Exception as e:
        return {'error': str(e)}

def main():
    # Read postcodes
    postcodes_file = '/home/alexandre/properties/data/CF24_4_postcodes.txt'
    with open(postcodes_file, 'r') as f:
        postcodes = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(postcodes)} postcodes...")

    results = []
    errors = []

    for i, postcode in enumerate(postcodes, 1):
        print(f"[{i}/{len(postcodes)}] Processing {postcode}...", end=' ')
        result = extract_housing_tenure(postcode)

        if 'error' in result:
            print(f"ERROR: {result['error']}")
            errors.append(postcode)
            results.append({
                'postcode': postcode,
                'social_count': 'Error',
                'social_pct': 'Error'
            })
        else:
            print(f"OK (Social: {result['social_count']}, {result['social_pct']}%)")
            results.append({
                'postcode': result['postcode'],
                'social_count': result['social_count'],
                'social_pct': result['social_pct']
            })

        # Be respectful - small delay between requests
        if i < len(postcodes):
            time.sleep(0.5)

    # Sort by social housing percentage (descending)
    def sort_key(r):
        if r['social_pct'] == 'Error':
            return -1  # Errors go to bottom
        return r['social_pct']

    results_sorted = sorted(results, key=sort_key, reverse=True)

    # Write CSV
    output_file = '/home/alexandre/properties/data/CF24_4_Housing_Tenure_Summary.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['postcode', 'social_count', 'social_pct'])
        writer.writeheader()
        for row in results_sorted:
            writer.writerow({
                'postcode': row['postcode'],
                'social_count': row['social_count'],
                'social_pct': f"{row['social_pct']}%" if row['social_pct'] != 'Error' else 'Error'
            })

    print(f"\n✓ Processed {len(postcodes)} postcodes")
    print(f"✓ Errors: {len(errors)}")
    print(f"✓ Output: {output_file}")

    if errors:
        print(f"\nPostcodes with errors: {', '.join(errors)}")

if __name__ == '__main__':
    main()
