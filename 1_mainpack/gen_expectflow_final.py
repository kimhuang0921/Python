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
    "load_runtime": "/projects/ga0/patterns/scan/eval/Scan/0516/rv_rcc_rvf_ldu_top_int_sa_scan_edt_pl_051525_2.stil.gz",
    "rv_mbist_preamble_0_40ns": "/projects/ga0/patterns/preamble/prod/bulk/rv_mbist_preamble_0/042525_8/rv_mbist_preamble_0_40ns_042525_8.stil",
    "rv_phy_d2dns_ctn_preamble_0": "/projects/ga0/patterns/preamble/prod/bulk/rv_phy_d2dns_preamble_0/051525_5/rv_phy_d2dns_ctn_preamble_0_051525_5.stil"        
}

PREAMBLE_DEFAULT = {
    'preamble1': 'rv_top_pad_reset_40ns',
    'preamble2': 'rv_top_volatilerawunlock_40ns',
    'preamble3': 'rv_scs_resetctn1ghz_tdr_40ns',
    'preamble4': 'rv_ss_resetClkDef_tdr_40ns',
}

PREAMBLE_CC = {
    'preamble1': 'rv_top_pad_reset_40ns',
    'preamble2': 'rv_top_volatilerawunlock_40ns',
    'preamble3': 'load_runtime'
}

PREAMBLE_CHARLES = {
    'preamble1': 'rv_mbist_preamble_0_40ns'
}

PREAMBLE_DELBERT = {
    'preamble1': 'rv_phy_d2dns_ctn_preamble_0'
}

DEFAULT_COLUMNS = {
    'Binning': '1', 'CLK': 'JTAG_TCK 25MHz + ref clk 100MHz', 'Comments': '', 'Frequency': '25 MHz',
    'IP': 'CORE', 'Limit High': '9999', 'Limit Low': '0', 'TP rev': 'A0',
    'Test Objective': 'Functional', 'Test instument': 'V93K',
    'Test item': 'Main', 'Test type': 'SCAN', 'TestMethod': '[Pattern Test]  Multiple register readout on JTAG_TDO & Compare by Tester',
    'Voltage condition': 'NV'
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
        continuity_removed = False
        base = re.sub(r'_continuity', '', base)
        if base != original_base:
            print(f"[WARNING] Removed 'continuity' from filename: {original_base}{timestamp} -> {base}{timestamp}")
            continuity_removed = True
        testname = base + timestamp
        # Normalize timestamp for lookup (remove leading underscore)
        timestamp = timestamp.lstrip('_') if timestamp else ''
        return testname, timestamp, continuity_removed
    return None, None, False

def build_filename_lookup(df):
    lookup = {}
    valid_rows = 0  # Initialize valid_rows
    for _, row in df.iterrows():
        if not isinstance(row.get('Pattern directory', ''), str) or not row['Pattern directory'].strip() or not str(row.get('Released by', '')).strip():
            continue
        valid_rows += 1
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            continue
        filename = os.path.basename(full_path)
        testname, _, _ = extract_testname_and_timestamp(filename)
        if testname:
            lookup[testname] = filename
    return lookup, valid_rows

def build_ts_lookup(df):
    ts_dict = {}
    valid_rows = 0  # Initialize valid_rows
    for _, row in df.iterrows():
        if not isinstance(row.get('Pattern directory', ''), str) or not row['Pattern directory'].strip() or not str(row.get('Released by', '')).strip():
            continue
        valid_rows += 1
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            continue
        filename = os.path.basename(full_path)
        testname, timestamp, _ = extract_testname_and_timestamp(filename)
        if testname and '_ts' in testname:
            prefix = re.sub(r'_int_sa_edt_ts.*$', '', testname)
            ts_dict.setdefault(timestamp, {})[prefix] = testname
    return ts_dict, valid_rows

def build_bscan_lookup(df):
    bscan_map = {}
    valid_rows = 0  # Initialize valid_rows
    for _, row in df.iterrows():
        if not isinstance(row.get('Pattern directory', ''), str) or not row['Pattern directory'].strip() or not str(row.get('Released by', '')).strip():
            continue
        valid_rows += 1
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            continue
        filename = os.path.basename(full_path)
        if 'bscan' not in filename:
            continue
        testname, timestamp, _ = extract_testname_and_timestamp(filename)
        if not testname:
            continue
        parts = testname.split('_')
        try:
            bscan_index = parts.index('bscan')
        except ValueError:
            continue
        prefix = '_'.join(parts[:bscan_index + 1])
        function = parts[bscan_index + 1]
        suffix_parts = parts[bscan_index + 2:]
        core_key = '_'.join([p for p in suffix_parts if not p.startswith('dbg')])
        group_key = f"{prefix}#{core_key}"
        group = bscan_map.setdefault(group_key, {'preamble': '', 'payloads': []})
        if 'preamb' in testname:
            group['preamble'] = testname
        else:
            group['payloads'].append(testname)
    return bscan_map, valid_rows

def classify_and_generate(df):
    valid_rows = 0
    filename_lookup, filename_valid_rows = build_filename_lookup(df)
    ts_lookup, ts_valid_rows = build_ts_lookup(df)
    bscan_lookup, bscan_valid_rows = build_bscan_lookup(df)
    valid_rows = filename_valid_rows  # Use filename_valid_rows as primary count
    results = []
    testname_counter = Counter()
    valid_patterns = []
    ts_patterns = []
    continuity_patterns = []
    bscan_preamb_patterns = []
    skipped_patterns = []

    for _, row in df.iterrows():
        if not isinstance(row.get('Pattern directory', ''), str) or not row['Pattern directory'].strip() or not str(row.get('Released by', '')).strip():
            skipped_patterns.append((row.get('debug pattern name', 'Unknown'), 'Empty or invalid Pattern directory or Released by'))
            continue
        valid_rows += 1
        released_by = row['Released by']
        full_path = row['Pattern directory']
        if not isinstance(full_path, str) or not full_path.strip():
            skipped_patterns.append((row.get('debug pattern name', 'Unknown'), 'Invalid full path'))
            continue
        filename = os.path.basename(full_path)

        testname, timestamp, continuity_removed = extract_testname_and_timestamp(filename)
        if not testname:
            skipped_patterns.append((filename, 'Invalid testname format'))
            continue

        lower = testname.lower()

        # Collect _ts patterns
        if '_ts' in lower:
            ts_patterns.append(testname)
            continue

        # Collect continuity patterns
        if continuity_removed:
            continuity_patterns.append(testname)
            continue

        # Collect bscan_preamb patterns
        if 'bscan' in lower and 'preamb' in lower:
            bscan_preamb_patterns.append(testname)
            continue

        testname_counter[testname] += 1
        count = testname_counter[testname]
        testname_versioned = f"{testname}_v{count-1}" if count > 1 else testname

        entry = {k: '' for k in ['test name', 'preamble1', 'preamble2', 'preamble3', 'preamble4', 'preamble5', 'preamble6']}
        entry['test name'] = testname_versioned

        if '_scan' in lower or '_chain' in lower:
            entry = {k: '' for k in entry.keys()}
            entry['test name'] = testname_versioned
            entry.update(PREAMBLE_DEFAULT)
            prefix = re.sub(r'_int_sa_(scan|chain)_edt_pl.*$', '', testname)
            ts_dict = ts_lookup.get(timestamp or '', {})
            entry['preamble5'] = ts_dict.get(prefix, '')
        elif 'bscan' in lower:
            parts = testname.split('_')
            try:
                bscan_index = parts.index('bscan')
                prefix = '_'.join(parts[:bscan_index + 1])
                suffix_parts = parts[bscan_index + 2:]
                core_key = '_'.join([p for p in suffix_parts if not p.startswith('dbg')])
                group_key = f"{prefix}#{core_key}"
            except ValueError:
                skipped_patterns.append((testname, 'Invalid bscan format'))
                continue

            group = bscan_lookup.get(group_key, {})
            if 'preamb' in testname:
                continue
            preamble_name = group.get('preamble', '')
            if not preamble_name:
                print(f"[WARN] No preamble found for BSCAN group: {group_key}")
                skipped_patterns.append((testname, 'No preamble for BSCAN group'))
                continue

            entry = {k: '' for k in entry.keys()}
            entry['test name'] = testname_versioned
            entry['preamble5'] = preamble_name
            entry.update(PREAMBLE_DEFAULT)
        elif released_by.strip().lower() == 'cc':
            entry = {k: '' for k in entry.keys()}
            entry['test name'] = testname_versioned
            entry.update(PREAMBLE_CC)
        elif released_by.strip().lower() == 'charles':
            entry = {k: '' for k in entry.keys()}
            entry['test name'] = testname_versioned
            entry.update(PREAMBLE_CHARLES)
        elif released_by.strip().lower() == 'delbert':
            entry = {k: '' for k in entry.keys()}
            entry['test name'] = testname_versioned
            entry.update(PREAMBLE_DELBERT)
        else:
            entry.update(PREAMBLE_DEFAULT)
            entry['test name'] = testname_versioned

        for i in range(1, 7):
            name = entry.get(f'preamble{i}', '')
            full_path = filename_lookup.get(name, DEFAULT_PREAMBLE_LOC.get(name, ''))
            entry[f'preamble{i} loc'] = os.path.basename(full_path) if full_path else ''

        entry['pattern loc'] = filename_lookup.get(testname, '')
        entry['pattern'] = testname_versioned

        for col, val in DEFAULT_COLUMNS.items():
            entry[col] = val

        results.append(entry)
        valid_patterns.append(testname_versioned)

    df_final = pd.DataFrame(results)
    df_final = df_final.reindex(columns=EXPECTED_COLUMNS)
    summary_lines = []
    summary_lines.append(f"Total rows parsed: {len(df)}")
    summary_lines.append(f"Valid rows with release/path: {valid_rows}")
    summary_lines.append(f"\nValid Patterns ({len(valid_patterns)}):")
    summary_lines.extend([f"- {p}" for p in valid_patterns])
    summary_lines.append(f"\nTS Patterns (not included in output, {len(ts_patterns)}):")
    summary_lines.extend([f"- {p}" for p in ts_patterns])
    summary_lines.append(f"\nContinuity Patterns (not included in output, {len(continuity_patterns)}):")
    summary_lines.extend([f"- {p}" for p in continuity_patterns])
    summary_lines.append(f"\nBscan Preamble Patterns (not included in output, {len(bscan_preamb_patterns)}):")
    summary_lines.extend([f"- {p}" for p in bscan_preamb_patterns])
    summary_lines.append(f"\nSkipped Patterns ({len(skipped_patterns)}):")
    summary_lines.extend([f"- {p}: {reason}" for p, reason in skipped_patterns])
    return df_final, summary_lines

def main(input_csv, output_xlsx=None):
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        return None, None, None
    required_cols = ['Pattern directory', 'Released by']
    for col in required_cols:
        if col not in df.columns:
            print(f"[ERROR] Missing required column in input: {col}")
            return None, None, None
    initial_rows = len(df)
    df = df.drop_duplicates(subset=['Pattern directory'], keep='first')
    if len(df) < initial_rows:
        print(f"[INFO] Removed {initial_rows - len(df)} duplicate absolute paths")
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    output_df, summary_lines = classify_and_generate(df)
    if output_df.empty:
        print("[ERROR] No valid patterns found in input CSV")
        return None, None, None
    if not output_xlsx:
        output_xlsx = f"expectflow_{ts}.xlsx"
    try:
        output_df.to_excel(output_xlsx, index=False)
        print(f"[INFO] Wrote {len(output_df)} rows to {output_xlsx}")
    except Exception as e:
        print(f"[ERROR] Failed to write XLSX: {e}")
        return None, None, None
    full_path_df = df[['Pattern directory']].copy()
    full_path_df.columns = ['Full Path']
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    input_basename = os.path.splitext(os.path.basename(input_csv))[0]
    full_path_csv = f"{input_basename}_{ts}.csv"
    try:
        full_path_df.to_csv(full_path_csv, index=False)
        print(f"[INFO] Wrote full path CSV: {full_path_csv}")
    except Exception as e:
        print(f"[ERROR] Failed to write CSV: {e}")
        return None, None, None
    return output_xlsx, full_path_csv, summary_lines

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_csv', required=True, help='Input trial.csv file')
    parser.add_argument('--output_xlsx', help='Output Excel file (auto timestamp if not given)')
    args = parser.parse_args()
    main(args.input_csv, args.output_xlsx)