import os
import subprocess
import pandas as pd
import argparse
import traceback
from datetime import datetime
from stilrepackFinal import package_release, send_email_report, send_xlsx_only

def sanitize_csv(input_csv):
    df = pd.read_csv(input_csv)
    df['Pattern directory'] = df['Pattern directory'].astype(str)
    df['Released by'] = df['Released by'].astype(str)
    sanitized_csv = f"sanitized_{os.path.basename(input_csv)}"
    df.to_csv(sanitized_csv, index=False)
    return sanitized_csv

def run_expectflow(input_csv):
    from gen_expectflow_final import main as run_flow
    return run_flow(input_csv)  # return xlsx_path, full_path_csv, summary_lines  # return xlsx_path, full_path_csv

def check_flow_validity(xlsx_path):
    df = pd.read_excel(xlsx_path, sheet_name=0)
    issues = []

    for col in ['test name', 'pattern loc']:
        if col not in df.columns:
            issues.append(f"Missing required column: {col}")
        elif df[col].isnull().any():
            issues.append(f"Column {col} contains null/empty values")

    for col in df.columns:
        if df[col].astype(str).str.contains("\\s+$").any():
            issues.append(f"Column {col} has trailing whitespace")

    return issues


def cleanup_files(xlsx_path, fullpath_csv):
    try:
        if xlsx_path and os.path.exists(xlsx_path):
            os.remove(xlsx_path)
            print(f"[INFO] Deleted {xlsx_path}")
        if fullpath_csv and os.path.exists(fullpath_csv):
            os.remove(fullpath_csv)
            print(f"[INFO] Deleted {fullpath_csv}")
    except Exception as e:
        print(f"[CLEANUP-ERROR] Failed to delete generated files: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input trial CSV file')
    parser.add_argument('--xlsx-only', action='store_true', help='Generate and send XLSX only')


    args = parser.parse_args()

    try:
        clean_csv = sanitize_csv(args.input)
        xlsx_path, fullpath_csv, summary_lines = run_expectflow(clean_csv)

        errors = check_flow_validity(xlsx_path)
        if errors:
            send_email_report(
                subject="[RELEASE REPORT] FlowGen Validation - FAIL",
                body="\n".join(errors),
                config=None
            )
            print("[ERROR] Validation failed. Email sent.")
            return

        if args.xlsx_only:
            # XLSX-only mode: send XLSX without packaging
            send_xlsx_only(xlsx_path, config=None, extra_info='\n'.join(summary_lines))
            
            print("[INFO] XLSX generated and sent.")
        else:
            # Full packaging mode
            df_paths = pd.read_csv(fullpath_csv)
            input_base = os.path.splitext(os.path.basename(args.input))[0]  # Use input CSV name
            package_release(df_paths, input_name=input_base, xlsx_path=xlsx_path, extra_info='\n'.join(summary_lines))
        cleanup_files(xlsx_path, fullpath_csv)

    except Exception as e:
        tb = traceback.format_exc()
        send_email_report(
            subject="[RELEASE REPORT] MainPack Exception - FAIL",
            body=f"Exception occurred:\n{tb}",
            config=None
        )
        print("[ERROR] Exception occurred. Email sent.")

if __name__ == "__main__":
    main()
