"""Bounded stdin protocol for notifier. No credentials, schema creation or writes."""
import json,sys
from datetime import datetime,timezone
from core.storage import ROOT
from core.readonly_state import ReadOnlyState,idea_rows
from core.entry_publication import check

def main():
    try:
        raw=sys.stdin.read(65537)
        if len(raw)>65536:raise ValueError('INPUT_TOO_LARGE')
        guard=json.loads(raw);s=ReadOnlyState(ROOT/'runtime/aegis.sqlite')
        try:
            from core.observed_context import evaluate
            from news.engine import NewsProvider
            ctx=evaluate(s,datetime.now(timezone.utc));news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(datetime.now(timezone.utc))
            rows=idea_rows(ROOT/'runtime/ideas.sqlite');ident=guard['proposal']['signal_id']
            row=next((r for r in rows if r['signal_id']==ident),None)
            reason='REGISTERED_PLAN_UNAVAILABLE' if row is None else check(guard,ctx,news,datetime.now(timezone.utc),row)
        finally:s.close()
        q=ctx.get('quote') or {}
        print(json.dumps({'eligible':reason is None,'reason':reason,'checked_at':datetime.now(timezone.utc).isoformat(),'source_at':q.get('source_timestamp'),'received_at':q.get('received_timestamp'),'reference_midpoint':(q.get('payload') or {}).get('mid'),'proposal_sha256':guard.get('sha256')}))
    except Exception:print(json.dumps({'eligible':False,'reason':'READ_ONLY_REVALIDATION_UNAVAILABLE'}))

if __name__=='__main__':main()
