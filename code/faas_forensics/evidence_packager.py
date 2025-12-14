import boto3
import json
import hashlib
import time


# CONFIGURATION

BUCKET_NAME = "faas-forensics-nivetha"
SNAPSHOT_PREFIX = "snapshots/"
LOG_PREFIX = "logs/"
EVIDENCE_PREFIX = "evidence/"
REGION = "eu-north-1"

s3 = boto3.client("s3", region_name=REGION)


# HELPER FUNCTIONS


def get_latest_file(prefix):
    """
    Fetches the latest file from an S3 prefix based on LastModified timestamp
    """
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    files = response.get("Contents", [])

    if not files:
        raise Exception(f"No files found under prefix: {prefix}")

    latest_file = sorted(files, key=lambda x: x["LastModified"], reverse=True)[0]
    return latest_file["Key"]


def download_json(key):
    """
    Downloads and parse a JSON object from S3
    """
    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return json.loads(response["Body"].read())


def compute_sha256(data):
    """
    Computes SHA-256 hash for integrity verification
    """
    serialized = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(serialized).hexdigest()


def generate_overview(function_name, anomaly_data):
    """
    Generates a dynamic, human-readable forensic overview
    """
    if anomaly_data.get("anomaly_detected"):
        reasons = ", ".join(anomaly_data.get("reasons", []))
        return (
            f"This forensic evidence bundle documents anomalous execution behavior "
            f"observed in the AWS Lambda function '{function_name}'. "
            f"The system detected abnormal patterns including: {reasons}. "
            f"This evidence was automatically collected to support post-incident "
            f"forensic investigation in an ephemeral serverless (FaaS) environment."
        )
    else:
        return (
            f"This forensic evidence bundle captures the configuration and runtime "
            f"behavior of the AWS Lambda function '{function_name}' during normal execution. "
            f"No anomalous behavior was detected in the observed execution window. "
            f"The collected evidence establishes a forensic baseline for future analysis "
            f"in a serverless (FaaS) environment."
        )


# MAIN EXECUTION


if __name__ == "__main__":

    print("[*] Fetching latest configuration snapshot and logs from S3...")

    # Fetches latest snapshot and log files
    snapshot_key = get_latest_file(SNAPSHOT_PREFIX)
    log_key = get_latest_file(LOG_PREFIX)

    snapshot_data = download_json(snapshot_key)
    log_data = download_json(log_key)

    # Loads anomaly detection output (local file)
    with open("anomaly_report.json", "r") as f:
        anomaly_data = json.load(f)

    # Generates dynamic overview
    overview_text = generate_overview(
        function_name=log_data.get("function_name"),
        anomaly_data=anomaly_data
    )

    # Builds forensic evidence bundle
    evidence_bundle = {
        "case_id": f"case-{int(time.time())}",
        "overview": overview_text,
        "function_name": log_data.get("function_name"),
        "configuration_snapshot": snapshot_data,
        "runtime_logs": log_data,
        "anomaly_report": anomaly_data,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }

    # Adds integrity hash
    evidence_bundle["sha256_hash"] = compute_sha256(evidence_bundle)

    # Uploads to S3
    evidence_key = f"{EVIDENCE_PREFIX}{evidence_bundle['case_id']}.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=evidence_key,
        Body=json.dumps(evidence_bundle, indent=2),
        ServerSideEncryption="AES256"
    )

    print(f"[✓] Evidence bundle successfully uploaded to:")
    print(f"    s3://{BUCKET_NAME}/{evidence_key}")
