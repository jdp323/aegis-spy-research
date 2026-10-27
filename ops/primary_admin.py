"""Explicit local administrative closure; never a market exit or private fill."""
import argparse,json
from datetime import datetime,timezone
from core.storage import Store,ROOT
from core.readonly_state import idea_rows
from core.primary_plan import administrative_close

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('signal_id');p.add_argument('--reason',required=True);args=p.parse_args()
    s=Store()
    try:print(json.dumps(administrative_close(s,idea_rows(ROOT/'runtime/ideas.sqlite'),args.signal_id,args.reason,datetime.now(timezone.utc))))
    finally:s.close()
if __name__=='__main__':main()
