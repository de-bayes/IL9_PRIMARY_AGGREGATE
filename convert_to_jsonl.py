#!/usr/bin/env python3
"""
Convert historical_snapshots.json from JSON array to JSONL format
"""

import json
import os
import shutil
from datetime import datetime

def convert_json_to_jsonl(input_file, output_file):
    """
    Convert JSON array file to JSONL (JSON Lines) format
    Each snapshot becomes a single line
    """
    print(f"Converting {input_file} to JSONL format...")

    # Read the JSON array
    with open(input_file, 'r') as f:
        snapshots = json.load(f)

    print(f"Loaded {len(snapshots)} snapshots")

    # Create backup
    backup_file = input_file + '.pre-jsonl-backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(input_file, backup_file)
    print(f"✓ Backup created: {backup_file}")

    # Write as JSONL
    with open(output_file, 'w') as f:
        for snapshot in snapshots:
            f.write(json.dumps(snapshot) + '\n')

    print(f"✓ Converted to JSONL: {output_file}")

    # Verify
    line_count = 0
    with open(output_file, 'r') as f:
        for line in f:
            if line.strip():
                line_count += 1

    print(f"✓ Verified {line_count} lines in JSONL file")

    # Show file sizes
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    jsonl_size = os.path.getsize(output_file) / (1024 * 1024)

    print(f"\nFile sizes:")
    print(f"  Original JSON: {original_size:.2f} MB")
    print(f"  JSONL format: {jsonl_size:.2f} MB")
    print(f"  Space saved: {((original_size - jsonl_size) / original_size * 100):.1f}%")

def main():
    print("=" * 70)
    print("Convert to JSONL Format")
    print("=" * 70)
    print()

    json_file = 'data/historical_snapshots.json'
    jsonl_file = 'data/historical_snapshots.jsonl'

    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found")
        return

    convert_json_to_jsonl(json_file, jsonl_file)

    print("\n" + "=" * 70)
    print("Conversion Complete!")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Update app.py to use JSONL format")
    print(f"2. Test locally")
    print(f"3. Deploy to Railway")
    print(f"4. Old JSON file backed up and can be removed after verification")

if __name__ == '__main__':
    main()
