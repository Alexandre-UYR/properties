#!/usr/bin/env python3
"""
Process CF24 3 retry postcodes - fetch housing tenure data from StreetCheck
This script replicates the Housing-Tenure-basic agent logic.
"""
import urllib.request
import re
import csv
import sys
import time

def normalize_postcode_for_url(postcode):
    """Convert 'CF24 3BS' to 'cf243bs'"""
    return postcode.replace(' ', '').lower()

def extract_housing_tenure(html_content, postcode):
    """Extract housing tenure data from StreetCheck page using regex"""
    try:
        # Find the Housing Tenure section
        tenure_match = re.search(r'<h3>Housing Tenure.*?</table>', html_content, re.DOTALL | re.IGNORECASE)
        if not tenure_match:
            return None

        tenure_section = tenure_match.group(0)

        # Extract table rows with category and value
        # Pattern: <td>Category Name</td>\s*<td class="b">Value</td>
        row_pattern = r'<td>([^<]+)</td>\s*<td[^>]*>([0-9,]+)</td>'
        matches = re.findall(row_pattern, tenure_section, re.IGNORECASE)

        if not matches:
            return None

        # Build data dictionary
        data = {}
        for category, value in matches:
            category = category.strip()
            value = value.replace(',', '').strip()
            try:
                data[category.lower()] = int(value)
            except ValueError:
                data[category.lower()] = 0

        # Extract specific values
        council = data.get('rented: from council', 0)
        other_social = data.get('rented: other social', 0)
        owned_out = data.get('owned outright', 0)
        owned_mort = data.get('owned with mortgage', 0)
        shared = data.get('shared ownership', 0)

        # Handle the private landlord which might have longer text
        private = 0
        for key in data.keys():
            if 'private landlord' in key:
                private = data[key]
                break

        total = data.get('total', 0)

        if total == 0:
            return None

        # Calculate derived values
        social_count = council + other_social
        owned_count = owned_out + owned_mort

        return {
            'postcode': postcode,
            'social_count': social_count,
            'social_pct': f"{(social_count / total * 100):.2f}%",
            'owned_count': owned_count,
            'owned_pct': f"{(owned_count / total * 100):.2f}%",
            'shared_count': shared,
            'shared_pct': f"{(shared / total * 100):.2f}%",
            'private_count': private,
            'private_pct': f"{(private / total * 100):.2f}%"
        }

    except Exception as e:
        print(f"Error processing {postcode}: {e}", file=sys.stderr)
        return None

def process_batch(batch_file, output_csv):
    """Process a batch of postcodes"""
    postcodes = []
    with open(batch_file, 'r') as f:
        postcodes = [line.strip() for line in f if line.strip()]

    results = []
    errors = 0

    for i, postcode in enumerate(postcodes, 1):
        url_postcode = normalize_postcode_for_url(postcode)
        url = f"https://www.streetcheck.co.uk/postcode/{url_postcode}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                html_content = response.read().decode('utf-8')
                tenure_data = extract_housing_tenure(html_content, postcode)
                if tenure_data:
                    results.append(tenure_data)
                    print(f"[{i}/{len(postcodes)}] {postcode}: OK", file=sys.stderr)
                    time.sleep(0.5)  # Delay to avoid rate limiting
                else:
                    # No data found
                    results.append({
                        'postcode': postcode,
                        'social_count': 'Error',
                        'social_pct': 'Error',
                        'owned_count': 'Error',
                        'owned_pct': 'Error',
                        'shared_count': 'Error',
                        'shared_pct': 'Error',
                        'private_count': 'Error',
                        'private_pct': 'Error'
                    })
                    errors += 1
                    print(f"[{i}/{len(postcodes)}] {postcode}: No data", file=sys.stderr)
        except Exception as e:
            print(f"[{i}/{len(postcodes)}] {postcode}: Error - {e}", file=sys.stderr)
            results.append({
                'postcode': postcode,
                'social_count': 'Error',
                'social_pct': 'Error',
                'owned_count': 'Error',
                'owned_pct': 'Error',
                'shared_count': 'Error',
                'shared_pct': 'Error',
                'private_count': 'Error',
                'private_pct': 'Error'
            })
            errors += 1

    # Write CSV
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
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

        for row in results:
            writer.writerow([
                row['postcode'],
                row['social_count'],
                row['social_pct'],
                row['owned_count'],
                row['owned_pct'],
                row['shared_count'],
                row['shared_pct'],
                row['private_count'],
                row['private_pct']
            ])

    return len(results), errors

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: process_retry.py <batch_file> <output_csv>")
        sys.exit(1)

    batch_file = sys.argv[1]
    output_csv = sys.argv[2]

    rows, errors = process_batch(batch_file, output_csv)
    print(f"Processed {rows} postcodes, {errors} errors")
    print(f"Output: {output_csv}")
