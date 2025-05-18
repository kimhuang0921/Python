# stilrepack.py

import os
import json
import shutil
import pandas as pd
from datetime import datetime
import tarfile
import argparse
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import subprocess
from aspera_upload import upload_with_aspera

# Load configuration from JSON file
CONFIG_FILE = "repack_config.json"
try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"[ERROR] Failed to load config file {CONFIG_FILE}: {e}")
    exit(1)

remote_dir = config.get("remote_dir", "/projects/ga0/patterns")
script_dir = os.path.dirname(os.path.abspath(__file__))
local_dir = os.path.join(script_dir, config.get("local_dir", "local"))
attachment_files = config.get("attachments", [])
base_dir = config.get("remote_dir", "/projects/ga0/patterns")
os.makedirs(local_dir, exist_ok=True)

# Email helper function to send reports with attachments
def send_email_report(subject, body, config=None, tarball_path=None, xlsx_path=None):
    if config is None:
        config = globals()['config']
    if "email" not in config:
        print("[WARNING] No email configuration found in config")
        return
    try:
        smtp_info = config["email"]
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = "IntelliGen <no-reply@stilrepack.com>"
        msg.add_header("Reply-To", smtp_info["from"])
        msg["To"] = ", ".join(smtp_info["to"])
        
        # Add body text
        msg.attach(MIMEText(body, "plain"))
        
        # Attach XLSX if provided
        if xlsx_path and os.path.isfile(xlsx_path):
            with open(xlsx_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(xlsx_path)}"
            )
            msg.attach(part)
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_info["from"], smtp_info["password"])
            server.send_message(msg)
        print("[INFO] Email sent successfully")
    except Exception as e:
        print(f"[MAIL-ERROR] Failed to send email: {e}")

# Function to send XLSX only
def send_xlsx_only(xlsx_path, config=None, extra_info=None):
    try:
        subject = f"[RELEASE REPORT] XLSX Generated - PASS"
        body = f"XLSX file generated successfully:\n📄 Output: {xlsx_path}"
        if extra_info:
            body += f"\n\n📊 Execution Summary:\n{extra_info}"
        send_email_report(subject, body, config, xlsx_path=xlsx_path)
    except Exception as e:
        print(f"[MAIL-ERROR] Failed to send XLSX: {e}")

# Main function to package release
def package_release(df, dry_run=False, output_path=None, input_name=None, xlsx_path=None, extra_info=None):
    results = []
    start_time = time.time()
    timestamp = datetime.now().strftime("%m%d%H%M")
    release_root = config.get("release_root", os.path.join(local_dir, "release"))
    release_dir_name = f"release_{input_name}_{timestamp}" if input_name else f"release_{timestamp}"
    release_dir = os.path.join(release_root, release_dir_name)
    bscan_dir = os.path.join(release_root, release_dir_name, "bscan")

    if dry_run:
        print(df["Full Path"].to_string(index=False))
        return

    try:
        os.makedirs(release_dir, exist_ok=True)
        os.makedirs(bscan_dir, exist_ok=True)
    except Exception as e:
        print(f"[ERROR] Failed to create directories {release_dir}: {e}")
        return

    # Track copy duration
    copy_start_time = time.time()
    print("[INFO] Copying files...")

    # Copy files to first-level directories using rsync
    for path in df["Full Path"]:
        path = path.strip()
        if not path:
            print("[INVALID] Skipping empty path")
            results.append((path, "INVALID"))
            continue
        if path.startswith(base_dir):
            rel_path = os.path.relpath(path, base_dir)
            first_level = rel_path.split(os.sep)[0]
            dest_path = os.path.join(release_dir, first_level, os.path.basename(path))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            try:
                subprocess.run(
                    ["rsync", "-a", path, dest_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
                results.append((path, "OK"))
            except subprocess.CalledProcessError as e:
                print(f"[RSYNC-ERROR] Failed to copy {path}: {e.stderr}")
                results.append((path, f"ERROR: {e.stderr}"))
        else:
            print(f"[INVALID] Skipping invalid path: {path}")
            results.append((path, "INVALID"))

    copy_duration = time.time() - copy_start_time

    # Verify copied files
    success = len([r for r in results if r[1] == "OK"])
    errors = len([r for r in results if r[1].startswith("ERROR")])
    invalid = len([r for r in results if r[1] == "INVALID"])
    print(f"[INFO] File verification completed: {success} OK, {errors} errors, {invalid} invalid")

    # Copy attachment files
    for file_name in attachment_files:
        local_path = os.path.join(local_dir, file_name)
        if os.path.isfile(local_path):
            try:
                shutil.copy(local_path, os.path.join(release_dir, file_name))
            except Exception as e:
                print(f"[ERROR] Failed to copy attachment {file_name}: {e}")

    # Track compression duration
    compress_start_time = time.time()
    print("[INFO] Compressing...")

    # Create compressed tarball
    tar_path = output_path if output_path else os.path.join(release_root, f"{release_dir_name}.tar.gz")
    try:
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(release_dir, arcname=os.path.basename(release_dir))
        shutil.rmtree(release_dir, ignore_errors=True)
    except Exception as e:
        print(f"[ERROR] Failed to create tarball {tar_path}: {e}")
        return

    compress_duration = time.time() - compress_start_time
    total_duration = time.time() - start_time

    # Log completion
    print(f"[INFO] Packaging completed: {tar_path}")
    print(f"[TIMING] Copy: {copy_duration:.2f}s, Compress: {compress_duration:.2f}s, Total: {total_duration:.2f}s")

    # Generate report with only problematic files
    status = "PASS" if errors == 0 and invalid == 0 else "FAIL"
    subject = f"[RELEASE REPORT] {input_name or 'Unnamed'} - {len(results)} patterns - {status}"
    body_lines = [
        f"✅ {success} files copied successfully",
    ]
    if extra_info:
        body_lines.append("")
        body_lines.append("📊 Execution Summary:")
        body_lines.append(extra_info)
    if errors > 0:
        body_lines.append(f"❌ {errors} files failed to copy:")
        body_lines.extend([f"- {r[0]}: {r[1]}" for r in results if r[1].startswith("ERROR")])
    if invalid > 0:
        body_lines.append(f"⚠️ {invalid} invalid paths:")
        body_lines.extend([f"- {r[0]}" for r in results if r[1] == "INVALID"])
    body_lines.extend([
        "",
        f"🕒 Copy Duration: {copy_duration:.2f} seconds",
        f"🕒 Compress Duration: {compress_duration:.2f} seconds",
        f"🕒 Total Duration: {total_duration:.2f} seconds",
        f"📦 Output: {tar_path}"
    ])
    body = "\n".join(body_lines)
    
    # Send email with XLSX attachment if successful
    send_email_report(subject, body, config, xlsx_path=xlsx_path if status == "PASS" else None)

    # Upload tarball to Aspera server if successful
    if status == "PASS":
        print("[INFO] Uploading tarball to Aspera server...")
        try:
            upload_with_aspera(
                local_path=tar_path,
                server="aspera.guc-asic.com",
                username="rivos",
                remote_path="/from Rivos",
                password=os.getenv("ASPERA_SCP_PASS", "e2URn5Jk"),
                port=3301,
                max_rate="100m",
                ascp_path="/home/kimhuang/.aspera/connect/bin/ascp"
            )
        except Exception as e:
            print(f"[ASPERA-ERROR] Failed to upload tarball: {e}")

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Input CSV file path")
    parser.add_argument("--dry-run", action="store_true", help="Print paths without copying or packaging")
    parser.add_argument("--output", help="Custom .tar.gz output path")
    args = parser.parse_args()

    if not args.csv or not os.path.isfile(args.csv):
        print("[ERROR] Please provide a valid --csv file")
        exit(1)

    try:
        input_base_name = os.path.splitext(os.path.basename(args.csv))[0]
        df = pd.read_csv(args.csv)
        if "Full Path" not in df.columns:
            print("[ERROR] CSV must contain 'Full Path' column")
            exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        exit(1)

    package_release(df, dry_run=args.dry_run, output_path=args.output, input_name=input_base_name)
