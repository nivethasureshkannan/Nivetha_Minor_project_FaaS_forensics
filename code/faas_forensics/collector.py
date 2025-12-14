import boto3, json, time, os

# AWS clients
logs = boto3.client('logs', region_name='eu-north-1')
s3 = boto3.client('s3', region_name='eu-north-1')


BUCKET = 'faas-forensics-nivetha'

def collect_logs(function_name, last_minutes=30):
    """Fetch logs from CloudWatch and save parsed summary to S3."""
    log_group = f"/aws/lambda/{function_name}"
    end_time = int(time.time() * 1000)
    start_time = end_time - last_minutes * 60 * 1000

    print(f"\nCollecting logs for {function_name} from last {last_minutes} minutes...")

    # Gets log events using paginator (handles multiple pages of logs)
    events = []
    paginator = logs.get_paginator('filter_log_events')

    try:
        for page in paginator.paginate(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time
        ):
            events.extend(page.get('events', []))

        print(f"Total events fetched: {len(events)}")

        # Parses logs for errors and execution time
        summary = parse_events(events)

        # Prepares JSON data
        data = {
            "function_name": function_name,
            "timestamp": int(time.time()),
            "parsed_summary": summary,
            "raw_event_count": len(events)
        }

        key = f"logs/{function_name}/{function_name}_{int(time.time())}.json"
        s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(data, indent=2).encode('utf-8'))

        print(f"Logs saved: s3://{BUCKET}/{key}")
        return key

    except Exception as e:
        print(f"Error fetching logs for {function_name}: {e}")
        return None


def parse_events(events):
    """Extract basic metrics like error count and duration."""
    error_count = 0
    durations = []
    for e in events:
        msg = e.get('message', '')
        if "ERROR" in msg or "Exception" in msg or "Traceback" in msg:
            error_count += 1
        if "Duration:" in msg and "ms" in msg:
            try:
                duration = float(msg.split("Duration:")[1].split(" ")[1])
                durations.append(duration)
            except:
                pass
    avg_duration = round(sum(durations)/len(durations), 2) if durations else None
    return {
        "error_count": error_count,
        "avg_duration_ms": avg_duration,
        "total_invocations": len(events)
    }


if __name__ == "__main__":
    funcs = ["demo-func-anom", "demo-func-normal"]
    for fn in funcs:
        collect_logs(fn, last_minutes=60)
