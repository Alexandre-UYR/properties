#!/usr/bin/env python3
"""
Batch worker for Housing Tenure data extraction.
Follows Housing-Tenure-basic agent logic.
"""
import sys
import csv
import re
import json
from pathlib import Path

def normalize_postcode_for_url(postcode):
    """Convert 'CF24 3AA' to 'cf243aa'"""
    return postcode.replace(" ", "").lower()

def normalize_postcode_display(postcode):
    """Ensure proper uppercase format"""
    return postcode.upper()

def extract_housing_tenure(html_content, postcode):
    """
    Extract Housing Tenure data from StreetCheck HTML.
    Returns dict with counts or None if data unavailable.
    """
    # Find the Housing Tenure table - look for table with heading
    tenure_pattern = r'<th colspan="2">Housing Tenure</th>.*?</tbody>\s*<tfoot>(.*?)</tfoot>'
    match = re.search(tenure_pattern, html_content, re.DOTALL | re.IGNORECASE)

    if not match:
        return None

    # Get the full table section including tbody
    table_pattern = r'<th colspan="2">Housing Tenure</th>.*?</tfoot>'
    table_match = re.search(table_pattern, html_content, re.DOTALL | re.IGNORECASE)

    if not table_match:
        return None

    tenure_html = table_match.group(0)

    # Extract values - look for td followed by td class="b"
    def extract_value(label):
        # Handle label variations
        if label == 'Rented: Private Landlord':
            pattern = r'<td[^>]*data-chart-title="Rented: Private Landlord"[^>]*>.*?</td>\s*<td class="b">([\d,]+)</td>'
        else:
            pattern = rf'<td>{re.escape(label)}</td>\s*<td class="b">([\d,]+)</td>'

        m = re.search(pattern, tenure_html, re.DOTALL)
        if m:
            return int(m.group(1).replace(',', ''))
        return 0

    try:
        council = extract_value('Rented: From Council')
        other_social = extract_value('Rented: Other Social')
        owned_out = extract_value('Owned Outright')
        owned_mort = extract_value('Owned with Mortgage')
        shared = extract_value('Shared Ownership')
        private = extract_value('Rented: Private Landlord')

        # Extract Total from tfoot
        total_pattern = r'<tfoot>.*?<td>Total</td>\s*<td class="b">([\d,]+)</td>'
        total_match = re.search(total_pattern, tenure_html, re.DOTALL)
        total = int(total_match.group(1).replace(',', '')) if total_match else 0

        if total == 0:
            return None

        social_count = council + other_social
        owned_count = owned_out + owned_mort

        def pct(val):
            return f"{(val/total)*100:.2f}%"

        return {
            'postcode': normalize_postcode_display(postcode),
            'social_count': social_count,
            'social_pct': pct(social_count),
            'owned_count': owned_count,
            'owned_pct': pct(owned_count),
            'shared_count': shared,
            'shared_pct': pct(shared),
            'private_count': private,
            'private_pct': pct(private)
        }
    except Exception as e:
        print(f"Error parsing {postcode}: {e}", file=sys.stderr)
        return None

def fetch_postcode_data(postcode):
    """Fetch data for a single postcode using curl"""
    import subprocess

    url_postcode = normalize_postcode_for_url(postcode)
    url = f"https://www.streetcheck.co.uk/postcode/{url_postcode}"

    try:
        result = subprocess.run(
            ['curl', '-s', '-L', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return extract_housing_tenure(result.stdout, postcode)
    except Exception as e:
        print(f"Error fetching {postcode}: {e}", file=sys.stderr)

    return None

def process_batch(postcodes_csv, sector, batch_num, out_dir):
    """
    Process a batch of postcodes and write CSV.
    Returns manifest dict.
    """
    postcodes = [pc.strip() for pc in postcodes_csv.split(',') if pc.strip()]
    sector_us = sector.replace(' ', '_')

    # Output file
    out_path = Path(out_dir) / f"{sector_us}_batch_{batch_num}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # CSV header (EXACT as specified)
    header = [
        'Postcode',
        'Council+Other Social (Count)',
        'Council+Other Social (%)',
        'Owned (Count)',
        'Owned (%)',
        'Shared Ownership (Count)',
        'Shared Ownership (%)',
        'Private Landlord (Count)',
        'Private Landlord (%)'
    ]

    rows = []
    error_count = 0

    for postcode in postcodes:
        data = fetch_postcode_data(postcode)

        if data is None:
            # Error row
            rows.append([
                normalize_postcode_display(postcode),
                'Error', 'Error', 'Error', 'Error',
                'Error', 'Error', 'Error', 'Error'
            ])
            error_count += 1
        else:
            rows.append([
                data['postcode'],
                str(data['social_count']),
                data['social_pct'],
                str(data['owned_count']),
                data['owned_pct'],
                str(data['shared_count']),
                data['shared_pct'],
                str(data['private_count']),
                data['private_pct']
            ])

    # Write CSV
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    # Return manifest
    manifest = {
        'sector': sector,
        'batch': batch_num,
        'csv_path': str(out_path.absolute()),
        'rows': len(rows),
        'errors': error_count
    }

    return manifest

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: process_batch.py <postcodes_csv> <sector> <batch_num> <out_dir>")
        sys.exit(1)

    postcodes = sys.argv[1]
    sector = sys.argv[2]
    batch = sys.argv[3]
    out_dir = sys.argv[4]

    manifest = process_batch(postcodes, sector, batch, out_dir)
    print(json.dumps(manifest))
