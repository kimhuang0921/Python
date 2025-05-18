import pandas as pd
import re
import os
import argparse
from datetime import datetime
from collections import Counter

# Default preamble name → stil filename correspondence
DEFAULT_PREAMBLE_LOC = {
    "rv_top_pad_reset_40ns": "/projects/ga0/patterns/preamble/prod/rv_top_pad_reset/042325_7/rv_top_pad_reset_40ns_042325_7.stil",
    "rv_top_volatilerawunlock_40ns": "/projects/ga0/patterns/preamble/prod/rv_top_volatilerawunlock/041625_3/rv_top_volatilerawunlock_40ns_041625_3.stil",
    "rv_scs_resetctn1ghz_tdr_40ns": "/projects/ga0/patterns/preamble/prod/rv_scs_resetctn1ghz_tdr/050925_7/rv_scs_resetctn1ghz_tdr_40ns_050925_7.stil",
    "rv_ss_resetClkDef_tdr_40ns": "/projects/ga0/patterns/preamble/prod/rv_ss_resetClkDef_tdr/042525_7/rv_ss_resetClkDef_tdr_40ns_042525_7.stil",
    "load_runtime": "/projects/ga0/patterns/scan/eval/Scan/0516/rv_rcc_rvf_ldu_top_int_sa_scan_edt_pl_051525_2.stil.gz"
}

PREAMBLE_FIXED = {
    'preamble1': 'rv_top_pad_reset_40ns',
    'preamble2': 'rv_top_volatilerawunlock_40ns',
    'preamble3': 'rv_scs_resetctn1ghz_tdr_40ns',
    'preamble4': 'rv_ss_resetClkDef_tdr_40ns',
}

DEFAULT_COLUMNS = {
    'Binning': '1', 'CLK': '1GHz', 'Comments': '', 'Frequency': '1GHz',
    'IP': 'CORE', 'Limit High': '9999', 'Limit Low': '0', 'TP rev': 'A0',
    'Test Objective': 'Functional', 'Test instument': 'V93K',
    'Test item': 'Main', 'Test type': 'SCAN', 'TestMethod': 'default_method',
    'Voltage condition': '1.1V'
}

EXPECTED_COLUMNS = [
    'IP', 'Test item', 'Test Objective', 'Test type', 'TestMethod', 'CLK',
    'test name', 'preamble1', 'preamble2', 'preamble3', 'preamble4',
    'preamble5', 'preamble6', 'pattern', 'Voltage condition', 'TP rev',
    'preamble1 loc', 'preamble2 loc', 'preamble3 loc', 'preamble4 loc',
    'preamble5 loc', 'preamble6 loc', 'pattern loc',
    'Frequency', 'Limit High', 'Limit Low', 'Binning', 'Comments', 'Test instument'
]

def extract_testname_and_timestamp(filename):
    pattern = r'(.+?)(_\d{6}_\d+)?\.(stil|stil\.gz)'
    match = re.match(pattern, filename)
    if match:
        base = match.group(1)
        timestamp = match.group(2) or ''
        # Check if 'continuity' is present before removing
        original_base = base
        base = re.sub(r'_continuity', '', base)
        if base != original_base:
            print(f"[WARNING] Removed 'continuity' from filename: {original_base}{timestamp} -> {base}{timestamp}")
        testname = base + timestamp
        # Normalize timestamp for lookup (remove leading underscore)
        timestamp = timestamp.lstrip('_') if timestamp else ''
        return testname, timestamp
    return None, None

def build_filename_lookup(df):
    lookup = {}
    for _, row in df.iterrows():
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            continue
        filename = os.path.basename(full_path)
        testname, _ = extract_testname_and_timestamp(filename)
        if testname:
            lookup[testname] = filename
    return lookup

def build_ts_lookup(df):
    ts_dict = {}
    for _, row in df.iterrows():
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            continue
        filename = os.path.basename(full_path)
        testname, timestamp = extract_testname_and_timestamp(filename)
        if testname and '_ts' in testname:
            prefix = re.sub(r'_int_sa_edt_ts.*$', '', testname)
            ts_dict.setdefault(timestamp, {})[prefix] = testname
    return ts_dict

def classify_and_generate(df):
    filename_lookup = build_filename_lookup(df)
    ts_lookup = build_ts_lookup(df)
    results = []
    testname_counter = Counter()

    for _, row in df.iterrows():
        released_by = row['Released by']
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            continue
        if not isinstance(released_by, str):
            released_by = ''
        filename = os.path.basename(full_path)

        testname, timestamp = extract_testname_and_timestamp(filename)
        if not testname:
            continue

        # Count duplicates to append version number if needed
        testname_counter[testname] += 1
        count = testname_counter[testname]
        # Keep timestamp unless duplicate, then append _vN
        testname_versioned = f"{testname}_v{count-1}" if count > 1 else testname

        lower = testname.lower()
        entry = {k: '' for k in ['test name', 'preamble1', 'preamble2', 'preamble3', 'preamble4', 'preamble5', 'preamble6']}
        entry['test name'] = testname_versioned

        if '_ts' in lower:
            entry.update(PREAMBLE_FIXED)
            entry['preamble5'] = testname
        elif '_scan' in lower or '_chain' in lower:
            entry.update(PREAMBLE_FIXED)
            # Use a broader prefix to match _ts
            prefix = re.sub(r'_int_sa_(scan|chain)_edt_pl.*$', '', testname)
            ts_dict = ts_lookup.get(timestamp or '', {})
            entry['preamble5'] = ts_dict.get(prefix, '')
        elif released_by.strip().lower() == 'cc':
            entry['preamble1'] = PREAMBLE_FIXED['preamble1']
            entry['preamble2'] = PREAMBLE_FIXED['preamble2']
            entry['preamble3'] = 'load_runtime'
        else:
            entry.update(PREAMBLE_FIXED)

        for i in range(1, 7):
            name = entry.get(f'preamble{i}', '')
            full_path = filename_lookup.get(name, DEFAULT_PREAMBLE_LOC.get(name, ''))
            entry[f'preamble{i} loc'] = os.path.basename(full_path) if full_path else ''

        entry['pattern loc'] = filename_lookup.get(testname, '')

        for col, val in DEFAULT_COLUMNS.items():
            entry[col] = val

        entry['pattern'] = testname_versioned
        results.append(entry)

    df_final = pd.DataFrame(results)
    df_final = df_final.reindex(columns=EXPECTED_COLUMNS)
    return df_final

def main(input_csv, output_xlsx=None):
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        return None, None

    required_cols = ['Pattern directory', 'Released by']
    for col in required_cols:
        if col not in df.columns:
            print(f"[ERROR] Missing required column in input: {col}")
            return None, None

    # Remove duplicate absolute paths, keeping the first occurrence
    initial_rows = len(df)
    df = df.drop_duplicates(subset=['Pattern directory'], keep='first')
    if len(df) < initial_rows:
        print(f"[INFO] Removed {initial_rows - len(df)} duplicate absolute paths")

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    output_df = classify_and_generate(df)

    if output_df.empty:
        print("[ERROR] No valid patterns found in input CSV")
        return None, None

    if not output_xlsx:
        output_xlsx = f"expectflow_{ts}.xlsx"

    try:
        output_df.to_excel(output_xlsx, index=False)
        print(f"[INFO] Wrote {len(output_df)} rows to {output_xlsx}")
    except Exception as e:
        print(f"[ERROR] Failed to write XLSX: {e}")
        return None, None

    # Output Full Path
    full_path_df = df[['Pattern directory']].copy()
    full_path_df.columns = ['Full Path']
    full_path_csv = f"pattern_full_paths_{ts}.csv"
    try:
        full_path_df.to_csv(full_path_csv, index=False)
        print(f"[INFO] Wrote full path CSV: {full_path_csv}")
    except Exception as e:
        print(f"[ERROR] Failed to write CSV: {e}")
        return None, None

    return output_xlsx, full_path_csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_csv', required=True, help='Input trial.csv file')
    parser.add_argument('--output_xlsx', help='Output Excel file (auto timestamp if not given)')
    args = parser.parse_args()
    main(args.input_csv, args.output_xlsx)
