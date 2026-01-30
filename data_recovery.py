#!/usr/bin/env python3
"""
Data Recovery Script for IL9Cast
Deduplicates snapshots, analyzes gaps, and creates clean dataset
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import shutil

def parse_timestamp(ts_str):
    """Parse ISO timestamp string to datetime object"""
    # Handle both formats: with and without microseconds
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None

def load_snapshots(filepath):
    """Load snapshots with error recovery"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            print(f"✓ Loaded {len(data)} snapshots from {filepath}")
            return data
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {e}")
        print("Attempting line-by-line recovery...")

        snapshots = []
        with open(filepath, 'r') as f:
            content = f.read()

        # Try to extract valid JSON objects
        lines = content.split('\n')
        current_obj = ""
        brace_count = 0

        for line in lines:
            current_obj += line + "\n"
            brace_count += line.count('{') - line.count('}')

            if brace_count == 0 and current_obj.strip():
                try:
                    obj = json.loads(current_obj)
                    if isinstance(obj, list):
                        snapshots.extend(obj)
                    elif isinstance(obj, dict) and 'timestamp' in obj:
                        snapshots.append(obj)
                    current_obj = ""
                except:
                    current_obj = ""

        print(f"✓ Recovered {len(snapshots)} snapshots from corrupted file")
        return snapshots

def deduplicate_snapshots(snapshots):
    """Remove duplicate snapshots based on timestamp"""
    seen_timestamps = set()
    unique_snapshots = []
    duplicates = []

    for snapshot in snapshots:
        ts = snapshot.get('timestamp')
        if ts not in seen_timestamps:
            seen_timestamps.add(ts)
            unique_snapshots.append(snapshot)
        else:
            duplicates.append(snapshot)

    print(f"\nDeduplication Results:")
    print(f"  Original: {len(snapshots)} snapshots")
    print(f"  Unique: {len(unique_snapshots)} snapshots")
    print(f"  Duplicates removed: {len(duplicates)} snapshots")

    # Show examples of duplicates
    if duplicates:
        print(f"\n  Example duplicates:")
        for dup in duplicates[:5]:
            print(f"    - {dup.get('timestamp')}")

    return unique_snapshots

def analyze_gaps(snapshots):
    """Analyze time gaps in the data"""
    if len(snapshots) < 2:
        print("Not enough snapshots to analyze gaps")
        return [], []

    # Filter out any snapshots with invalid timestamps
    valid_snapshots = [s for s in snapshots if parse_timestamp(s.get('timestamp'))]
    # Sort by timestamp
    sorted_snapshots = sorted(valid_snapshots, key=lambda x: parse_timestamp(x['timestamp']))

    gaps = []
    for i in range(len(sorted_snapshots) - 1):
        ts1 = parse_timestamp(sorted_snapshots[i]['timestamp'])
        ts2 = parse_timestamp(sorted_snapshots[i+1]['timestamp'])

        if ts1 and ts2:
            gap = ts2 - ts1
            # Flag gaps larger than 5 minutes
            if gap > timedelta(minutes=5):
                gaps.append({
                    'start': sorted_snapshots[i]['timestamp'],
                    'end': sorted_snapshots[i+1]['timestamp'],
                    'duration': str(gap)
                })

    print(f"\n\nGap Analysis:")
    print(f"  Total snapshots: {len(sorted_snapshots)}")
    print(f"  Date range: {sorted_snapshots[0]['timestamp']} to {sorted_snapshots[-1]['timestamp']}")
    print(f"  Gaps > 5 minutes: {len(gaps)}")

    if gaps:
        print(f"\n  Major gaps:")
        for gap in gaps:
            print(f"    - {gap['start']} to {gap['end']} ({gap['duration']})")

    return gaps, sorted_snapshots

def analyze_millisecond_duplicates(snapshots):
    """Find snapshots within milliseconds of each other"""
    # Filter out any snapshots with invalid timestamps
    valid_snapshots = [s for s in snapshots if parse_timestamp(s.get('timestamp'))]
    sorted_snapshots = sorted(valid_snapshots, key=lambda x: parse_timestamp(x['timestamp']))

    millisecond_dupes = []
    for i in range(len(sorted_snapshots) - 1):
        ts1 = parse_timestamp(sorted_snapshots[i]['timestamp'])
        ts2 = parse_timestamp(sorted_snapshots[i+1]['timestamp'])

        if ts1 and ts2:
            diff = (ts2 - ts1).total_seconds()
            if 0 < diff < 1:  # Within 1 second
                millisecond_dupes.append({
                    'ts1': sorted_snapshots[i]['timestamp'],
                    'ts2': sorted_snapshots[i+1]['timestamp'],
                    'diff_ms': diff * 1000
                })

    if millisecond_dupes:
        print(f"\n\nMillisecond-Level Duplicates:")
        print(f"  Found {len(millisecond_dupes)} pairs within 1 second of each other")
        print(f"\n  Examples:")
        for dup in millisecond_dupes[:10]:
            print(f"    - {dup['ts1']} vs {dup['ts2']} (diff: {dup['diff_ms']:.1f}ms)")

    return millisecond_dupes

def save_clean_data(snapshots, output_path):
    """Save cleaned data with backup"""
    # Create backup of original
    if os.path.exists(output_path):
        backup_path = output_path + '.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(output_path, backup_path)
        print(f"\n✓ Backup created: {backup_path}")

    # Filter out any snapshots with invalid timestamps
    valid_snapshots = [s for s in snapshots if parse_timestamp(s.get('timestamp'))]
    # Sort by timestamp before saving
    sorted_snapshots = sorted(valid_snapshots, key=lambda x: parse_timestamp(x['timestamp']))

    # Write clean data
    with open(output_path, 'w') as f:
        json.dump(sorted_snapshots, f, indent=2)

    print(f"✓ Clean data saved: {output_path}")
    print(f"  Total snapshots: {len(sorted_snapshots)}")

    # Calculate file size
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  File size: {size_mb:.2f} MB")

def main():
    print("=" * 60)
    print("IL9Cast Data Recovery Tool")
    print("=" * 60)

    data_file = 'data/historical_snapshots.json'

    # Step 1: Load data
    print(f"\n[Step 1] Loading data from {data_file}...")
    snapshots = load_snapshots(data_file)

    # Step 2: Analyze millisecond duplicates
    print(f"\n[Step 2] Analyzing millisecond-level duplicates...")
    analyze_millisecond_duplicates(snapshots)

    # Step 3: Deduplicate
    print(f"\n[Step 3] Deduplicating snapshots...")
    unique_snapshots = deduplicate_snapshots(snapshots)

    # Step 4: Analyze gaps
    print(f"\n[Step 4] Analyzing time gaps...")
    gaps, sorted_snapshots = analyze_gaps(unique_snapshots)

    # Step 5: Save clean data
    print(f"\n[Step 5] Saving clean data...")
    save_clean_data(sorted_snapshots, data_file)

    print("\n" + "=" * 60)
    print("Recovery Complete!")
    print("=" * 60)

    # Summary statistics
    print(f"\nSummary:")
    print(f"  Original entries: {len(snapshots)}")
    print(f"  After deduplication: {len(unique_snapshots)}")
    print(f"  Duplicates removed: {len(snapshots) - len(unique_snapshots)}")
    print(f"  Major gaps (>5 min): {len(gaps)}")

    if gaps:
        # Find the 15-hour gap mentioned
        large_gaps = [g for g in gaps if 'hour' in g['duration'] and int(g['duration'].split()[0]) > 10]
        if large_gaps:
            print(f"\n  ⚠️  Large gaps found:")
            for gap in large_gaps:
                print(f"     {gap['start']} to {gap['end']} ({gap['duration']})")

if __name__ == '__main__':
    main()
