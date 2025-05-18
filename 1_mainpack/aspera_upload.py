import subprocess
import os
import shutil

def upload_with_aspera(local_path, server, username, remote_path, password, port=33001, max_rate="100m", ascp_path=None):
    """
    Upload a file or directory using Aspera's ascp command.

    Parameters:
        local_path (str): Path to the local file or directory.
        server (str): Aspera server address.
        username (str): Server username.
        remote_path (str): Destination path on the server.
        password (str): Server password.
        port (int): Aspera port (default: 33001).
        max_rate (str): Maximum transfer rate (e.g., "100m" for 100 Mbps).
        ascp_path (str): Absolute path to the ascp command (optional).
    """
    # Check if local path exists
    if not os.path.exists(local_path):
        print(f"Error: Local path {local_path} does not exist!")
        return

    # Determine ascp path
    if ascp_path is None:
        ascp_path = shutil.which("ascp") or "/home/kimhuang/.aspera/connect/bin/ascp"
    
    if not os.path.exists(ascp_path):
        print(f"Error: ascp path {ascp_path} does not exist. Please verify Aspera Connect installation!")
        return

    # Set environment variable for password
    env = os.environ.copy()
    env["ASPERA_SCP_PASS"] = password

    # Build ascp command
    ascp_cmd = [
        ascp_path,
        "-P", str(port),
        "-QT",
        "-l", max_rate,
        "-d",  # Enable directory recursion
        "--file-list", "-",  # Use file list for flexibility
        "--host", server,
        "--user", username,
        "--mode", "send",
        remote_path
    ]

    # Prepare file list (single file or directory contents)
    file_list = []
    if os.path.isfile(local_path):
        file_list.append(local_path)
    elif os.path.isdir(local_path):
        for root, _, files in os.walk(local_path):
            for file in files:
                file_list.append(os.path.join(root, file))

    if not file_list:
        print(f"Error: No files found to upload at {local_path}!")
        return

    try:
        # Execute ascp command with file list via stdin
        result = subprocess.run(
            ascp_cmd,
            input="\n".join(file_list),
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Upload successful!")
        print("Output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Upload failed!")
        print("Error message:", e.stderr)
    except FileNotFoundError:
        print(f"Error: Cannot execute {ascp_path}. Please verify the path.")
    except Exception as e:
        print(f"Error: Unexpected error during upload: {e}")

if __name__ == "__main__":
    # Configuration parameters
    local_path = "/projects/ga0/patterns/release/release_trial_05160047.tar.gz"
    server = "aspera.guc-asic.com"
    username = "rivos"
    remote_path = "/from Rivos"
    password = os.getenv("ASPERA_SCP_PASS", "e2URn5Jk")
    port = 33001
    max_rate = "100m"
    ascp_path = "/home/kimhuang/.aspera/connect/bin/ascp"

    # Perform upload
    upload_with_aspera(local_path, server, username, remote_path, password, port, max_rate, ascp_path)
