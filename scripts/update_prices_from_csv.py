#!/usr/bin/env python3
"""Update view_purchases_augmented.json with prices from completed CSV.

Usage:
    python scripts/update_prices_from_csv.py test_data/completed_prices.csv

This reads your completed CSV (with unit_price filled in), updates the
view_purchases_augmented.json file, then you can run the import:

    from src.services.enhanced_import_service import import_view
    result = import_view("test_data/view_purchases_augmented.json", mode="merge")
"""

import csv
import json
import sys
from pathlib import Path


def update_prices(csv_path: str, json_path: str = "test_data/view_purchases_augmented.json"):
    """Update JSON file with prices from CSV."""

    # Load CSV with prices
    prices_by_uuid = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            uuid = row.get('uuid', '').strip()
            price_str = row.get('unit_price', '').strip()
            if uuid and price_str:
                try:
                    # Strip dollar sign and commas if present
                    clean_price = price_str.lstrip('$').replace(',', '')
                    prices_by_uuid[uuid] = float(clean_price)
                except ValueError:
                    print(f"Warning: Invalid price '{price_str}' for uuid {uuid[:8]}...")

    print(f"Loaded {len(prices_by_uuid)} prices from CSV")

    # Load existing JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Update prices
    updated = 0
    for record in data['records']:
        uuid = record.get('uuid')
        if uuid in prices_by_uuid:
            old_price = record.get('unit_price', 0)
            new_price = prices_by_uuid[uuid]
            if old_price != new_price:
                record['unit_price'] = new_price
                # Recalculate total_cost if quantity exists
                qty = record.get('quantity_purchased', 1)
                record['total_cost'] = new_price * qty
                updated += 1

    print(f"Updated {updated} records in JSON")

    # Write back
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved to {json_path}")
    print(f"\nNext step: Run the import:")
    print(f"  from src.services.enhanced_import_service import import_view")
    print(f"  result = import_view('{json_path}', mode='merge')")
    print(f"  print(result.get_summary())")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_prices_from_csv.py <completed_prices.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    update_prices(csv_path)
