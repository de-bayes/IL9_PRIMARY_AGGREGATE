#!/usr/bin/env python3
"""
Aggressive Deduplication Script
Removes snapshots within 1 second of each other, keeping only the first
"""

import json
from datetime import datetime, timedelta
import os
import shutil

def parse_timestamp(ts_str):
    """Parse ISO timestamp string to datetime object"""
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None

def aggressive_deduplicate(snapshots, threshold_seconds=1.0):
    """
    Remove snapshots within threshold_seconds of each other
    Keeps the first snapshot, removes subsequent ones
    """
    # Filter and sort
    valid_snapshots = [s for s in snapshots if parse_timestamp(s.get('timestamp'))]
    sorted_snapshots = sorted(valid_snapshots, key=lambda x: parse_timestamp(x['timestamp']))

    if not sorted_snapshots:
        return []

    deduplicated = [sorted_snapshots[0]]
    removed = []

    for snapshot in sorted_snapshots[1:]:
        current_ts = parse_timestamp(snapshot['timestamp'])
        last_kept_ts = parse_timestamp(deduplicated[-1]['timestamp'])

        diff_seconds = (current_ts - last_kept_ts).total_seconds()

        if diff_seconds >= threshold_seconds:
            deduplicated.append(snapshot)
        else:
            removed.append({
                'timestamp': snapshot['timestamp'],
                'diff_ms': diff_seconds * 1000,
                'previous': deduplicated[-1]['timestamp']
            })

    print(f"\nAggressive Deduplication (threshold: {threshold_seconds}s):")
    print(f"  Original: {len(sorted_snapshots)} snapshots")
    print(f"  Kept: {len(deduplicated)} snapshots")
    print(f"  Removed: {len(removed)} duplicates")

    if removed:
        print(f"\n  Example removals:")
        for item in removed[:10]:
            print(f"    - Removed {item['timestamp']} ({item['diff_ms']:.1f}ms after {item['previous']})")

    return deduplicated

def main():
    print("=" * 70)
    print("Aggressive Deduplication - Remove Millisecond Duplicates")
    print("=" * 70)

    data_file = 'data/historical_snapshots.json'

    # Load data
    print(f"\nLoading {data_file}...")
    with open(data_file, 'r') as f:
        snapshots = json.load(f)
    print(f"✓ Loaded {len(snapshots)} snapshots")

    # Deduplicate
    print(f"\nProcessing...")
    clean_snapshots = aggressive_deduplicate(snapshots, threshold_seconds=1.0)

    # Backup original
    backup_path = data_file + '.pre-dedup-backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(data_file, backup_path)
    print(f"\n✓ Backup created: {backup_path}")

    # Save cleaned data
    with open(data_file, 'w') as f:
        json.dump(clean_snapshots, f, indent=2)

    size_mb = os.path.getsize(data_file) / (1024 * 1024)
    print(f"✓ Cleaned data saved: {data_file}")
    print(f"  File size: {size_mb:.2f} MB")

    # Final stats
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Before: {len(snapshots)} snapshots")
    print(f"  After: {len(clean_snapshots)} snapshots")
    print(f"  Reduction: {len(snapshots) - len(clean_snapshots)} snapshots ({((len(snapshots) - len(clean_snapshots)) / len(snapshots) * 100):.1f}%)")
    print("=" * 70)

if __name__ == '__main__':
    main()
