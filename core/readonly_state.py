"""Query-only facade: evaluation must not create schemas or write diagnostics."""
import json,sqlite3
from pathlib import Path

class ReadOnlyState:
    def __init__(self,path):
        self.db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)
        self.db.execute('PRAGMA query_only=ON')
    def get(self,key,default=None):
        r=self.db.execute('SELECT payload FROM state WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else default
    def snapshot(self,keys):
        self.db.execute('BEGIN')
        try:return {k:self.get(k) for k in keys}
        finally:self.db.rollback()
    def put(self,*a,**k):pass
    def close(self):self.db.close()

def idea_rows(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)
    try:return [json.loads(r[0]) for r in db.execute('SELECT payload FROM idea_events WHERE rowid IN (SELECT MAX(rowid) FROM idea_events GROUP BY signal_id)')]
    finally:db.close()
