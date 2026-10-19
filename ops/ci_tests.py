"""CI exit status mirrors isolated regression failures."""
import json
from ops.test_runner import run
if __name__=='__main__':
    result=run();print(json.dumps(result,indent=2));raise SystemExit(not result['successful'])
