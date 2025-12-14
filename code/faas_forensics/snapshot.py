import boto3, json, time, os

# AWS clients
lambda_cli = boto3.client('lambda', region_name='eu-north-1')
iam = boto3.client('iam')
s3 = boto3.client('s3', region_name='eu-north-1')


BUCKET = 'faas-forensics-nivetha'

def get_role_details(role_arn):
    """Fetch IAM role details used by the Lambda."""
    try:
        role_name = role_arn.split('/')[-1]
        response = iam.get_role(RoleName=role_name)
        return {
            "RoleName": role_name,
            "Arn": response["Role"]["Arn"],
            "CreateDate": str(response["Role"]["CreateDate"]),
            "AssumeRolePolicyDocument": response["Role"]["AssumeRolePolicyDocument"]
        }
    except Exception as e:
        return {"RoleArn": role_arn, "Error": str(e)}

def snapshot_function(function_name):
    """Captures full Lambda configuration and upload JSON to S3."""
    try:
        print(f"\nCapturing configuration snapshot for {function_name}...")
        config = lambda_cli.get_function_configuration(FunctionName=function_name)
        code_info = lambda_cli.get_function(FunctionName=function_name)["Code"]

        # Builds detailed snapshot
        snapshot = {
            "FunctionName": config.get("FunctionName"),
            "FunctionArn": config.get("FunctionArn"),
            "Runtime": config.get("Runtime"),
            "Handler": config.get("Handler"),
            "MemorySize": config.get("MemorySize"),
            "Timeout": config.get("Timeout"),
            "LastModified": config.get("LastModified"),
            "Description": config.get("Description"),
            "RoleDetails": get_role_details(config.get("Role")),
            "EnvironmentVariables": config.get("Environment", {}).get("Variables", {}),
            "TracingConfig": config.get("TracingConfig"),
            "VpcConfig": config.get("VpcConfig"),
            "CodeInfo": code_info,
            "RevisionId": config.get("RevisionId"),
            "KMSKeyArn": config.get("KMSKeyArn"),
            "State": config.get("State"),
            "PackageType": config.get("PackageType"),
            "Architectures": config.get("Architectures"),
            "EphemeralStorage": config.get("EphemeralStorage", {}),
            "SnapshotTimestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }

        key = f"snapshots/{function_name}/{function_name}_{int(time.time())}.json"
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=json.dumps(snapshot, indent=2).encode('utf-8')
        )
        print(f"Snapshot saved: s3://{BUCKET}/{key}")

    except Exception as e:
        print(f"Error capturing snapshot for {function_name}: {e}")

if __name__ == "__main__":
    functions = ["demo-func-anom", "demo-func-normal"]
    for fn in functions:
        snapshot_function(fn)
