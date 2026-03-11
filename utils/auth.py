import subprocess
import sys
import os


# --- Authentication Function ---
def gcloud_auth_login(key_file_path: str = None):
    """Checks gcloud authentication and logs in if necessary."""
    try:
        # Check if gcloud is installed
        subprocess.run(["gcloud", "--version"], check=True, capture_output=True, shell=os.name == "nt")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: gcloud command not found. Install Google Cloud SDK.")
        sys.exit(1)

    # Check for existing authentication
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            check=True, capture_output=True, text=True, shell=os.name == "nt"
        )
        if result.stdout.strip():
            print(f"✅ Authenticated as: {result.stdout.strip()}")
            return
    except subprocess.CalledProcessError:
        pass

    print("🟡 gcloud not authenticated. Logging in...")

    # key_file now uses the provided path, or falls back to env var/None
    key_file = key_file_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    try:
        if key_file and os.path.exists(key_file):
            # Service Account Authentication
            print(f"🔑 Activating service account from file: {key_file}")
            subprocess.run(
                ["gcloud", "auth", "activate-service-account", f"--key-file={key_file}"],
                check=True, capture_output=True, shell=os.name == "nt"
            )
        elif key_file and not os.path.exists(key_file):
            print(f"❌ ERROR: Service account key file not found at: {key_file}")
            sys.exit(1)
        else:
            # Interactive Login
            print("👤 Falling back to interactive browser login...")
            subprocess.run(
                ["gcloud", "auth", "login"], check=True
            )

        account_result = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            check=True, capture_output=True, text=True, shell=os.name == "nt"
        )
        print(f"✅ Successfully authenticated as: {account_result.stdout.strip()}")

    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Failed to authenticate.")
        print(f"Stderr: {e.stderr.strip()}")
        sys.exit(1)


# --- Deployment Command ---
cloud_command = [
    "gcloud", "compute", "instances", "create-with-container",
    "instance-20251016-143139",
    "--project=aixr-401704",
    "--zone=us-central1-f",
    "--machine-type=e2-medium",
    "--network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default",
    "--maintenance-policy=MIGRATE",
    "--provisioning-model=STANDARD",
    "--service-account=1004568990634-compute@developer.gserviceaccount.com",
    "--scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append",
    "--image=projects/cos-cloud/global/images/cos-109-17800-570-50",
    "--boot-disk-size=10GB",
    "--boot-disk-type=pd-balanced",
    "--boot-disk-device-name=instance-20251016-143139",
    "--container-image=python:3.10-slim",
    "--container-restart-policy=always",
    "--no-shielded-secure-boot",
    "--shielded-vtpm",
    "--shielded-integrity-monitoring",
    "--labels=goog-ec-src=vm_add-gcloud,container-vm=cos-109-17800-570-50"
]


def execute_deployment(command):
    """Executes the GCE VM creation command."""
    print("\n--- Starting GCE VM Deployment ---")
    print(f"Running command: {' '.join(command)}")

    try:
        # Execute the command, showing output directly
        subprocess.run(command, check=True, stdout=sys.stdout, stderr=sys.stderr)
        print("\n✅ VM Instance created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ DEPLOYMENT FAILED.")
        print(f"Error Code: {e.returncode}")
        print("Please check the project ID, service account permissions, and API enablement.")
        sys.exit(1)


if __name__ == '__main__':
    # 1. DEFINE LOCAL KEY FILE PATH HERE.
    # !!! REPLACE THIS PATH WITH THE ACTUAL PATH TO YOUR GCP SERVICE ACCOUNT JSON KEY FILE !!!
    LOCAL_KEY_FILE_PATH = r"C:\Users\bestb\PycharmProjects\BestBrain\auth\credentials.json"

    # 2. Ensure authentication is set up, prioritizing the local file
    gcloud_auth_login(key_file_path=LOCAL_KEY_FILE_PATH)

    # 3. Execute the deployment
    execute_deployment(cloud_command)