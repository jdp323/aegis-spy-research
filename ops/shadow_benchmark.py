"""Honest cold-start/model benchmark; absent dependencies remain unavailable."""
import argparse,json,sys,time
from pathlib import Path
from datetime import datetime,timezone
from core.storage import ROOT
from ops.shadow_worker import available_memory,MINIMUM_FREE_BYTES,step,bounded

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request');p.add_argument('--output',required=True);args=p.parse_args();start=time.monotonic()
    result={'at':datetime.now(timezone.utc).isoformat(),'free_bytes':available_memory(),'minimum_free_bytes':MINIMUM_FREE_BYTES,'model_smoke':'NOT_RUN','entry_control':False}
    home=ROOT/'.shadow-model';py=home/('venv/Scripts/python.exe' if sys.platform=='win32' else 'venv/bin/python')
    if result['free_bytes']<MINIMUM_FREE_BYTES:result['blocker']='INSUFFICIENT_RESOURCE_HEADROOM'
    elif not py.exists():result['blocker']='SEPARATE_MODEL_ENVIRONMENT_UNAVAILABLE'
    elif not args.request:result['blocker']='GENUINE_COMPLETED_INPUT_REQUEST_REQUIRED'
    else:
        request=json.loads(Path(args.request).read_text());runs=[bounded([str(py),'-X','utf8','-m','ops.kronos_infer',str(home)],request) for _ in range(2)]
        result['runs']=runs
        from research.shadow_forecast import validate_result,sha
        try:
            values=[validate_result(request,r['result'],datetime.now(timezone.utc)) for r in runs if r['status']=='COMPLETED']
            result['deterministic_raw_paths']=len(values)==2 and sha(values[0]['paths'])==sha(values[1]['paths']);result['model_smoke']='PASS' if result['deterministic_raw_paths'] else 'FAIL'
        except (ValueError,KeyError):result['model_smoke']='FAIL'
    result['benchmark_seconds']=time.monotonic()-start;Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
