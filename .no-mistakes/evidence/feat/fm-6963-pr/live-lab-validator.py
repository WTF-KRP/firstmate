#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
lab = Path(os.environ['FM_HOME'])
request = json.load(sys.stdin)
with (lab / 'requests.jsonl').open('a') as log:
    log.write(json.dumps(request, sort_keys=True) + '\n')
behavior = (lab / 'behavior').read_text().strip()
if behavior == 'refuse-id' and request['task_id'] in ('t-refuse', 'b-one'):
    print(f"lab policy refuses {request['task_id']} for project {request['project']}", file=sys.stderr)
    sys.exit(3)
if behavior == 'timeout':
    print('lab validator hanging', file=sys.stderr, flush=True)
    time.sleep(60)
print(json.dumps({"schema_version": 1, "decision": "allow", "request_sha256": request['request_sha256']}))
