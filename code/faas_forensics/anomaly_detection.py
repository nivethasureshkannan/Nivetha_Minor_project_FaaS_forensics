import boto3
import json
import time


# CONFIGURATION

BUCKET_NAME = "faas-forensics-nivetha"
LOG_PREFIX = "logs/"
REGION = "eu-north-1"

ERROR_THRESHOLD = 0
DURATION_THRESHOLD_MS = 12
INVOCATION_THRESHOLD = 50

s3 = boto3.client("s3", region_name=REGION)


# HELPER FUNCTIONS


def get_latest_log_file():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=LOG_PREFIX)
    files = response.get("Contents", [])

    if not files:
        raise Exception("No log files found in S3")

    latest = sorted(files, key=lambda x: x["LastModified"], reverse=True)[0]
    return latest["Key"]


def download_log_data(key):
    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return json.loads(response["Body"].read())


def detect_anomaly(log_data):
    reasons = []
    metrics = log_data.get("parsed_summary", {})

    error_count = metrics.get("error_count", 0)
    avg_duration = metrics.get("avg_duration_ms", 0)
    invocations = metrics.get("total_invocations", 0)

    if error_count > ERROR_THRESHOLD:
        reasons.append("Error count exceeded threshold")

    if avg_duration > DURATION_THRESHOLD_MS:
        reasons.append("Execution duration spike detected")

    if invocations > INVOCATION_THRESHOLD:
        reasons.append("High invocation frequency detected")

    return {
        "function_name": log_data.get("function_name"),
        "anomaly_detected": len(reasons) > 0,
        "reasons": reasons,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }


# MAIN EXECUTION


if __name__ == "__main__":

    print("[*] Fetching latest runtime logs from S3...")

    log_key = get_latest_log_file()
    log_data = download_log_data(log_key)
    print("DEBUG: Log data fetched from S3:")
    print(json.dumps(log_data, indent=2))


    anomaly_report = detect_anomaly(log_data)
    

    with open("anomaly_report.json", "w") as f:
        json.dump(anomaly_report, f, indent=2)

    print("[✓] Anomaly Detection Result:")
    print(json.dumps(anomaly_report, indent=2))
