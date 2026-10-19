"""Read-only ledger/control row and schema comparison. Never opens a missing database."""
import json,sqlite3,re
from datetime import datetime,timezone
from pathlib import Path
from core.storage import ROOT
def inspect(path):
    if not path.exists():return {'state':'ABSENT'}
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        tables={}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            if not re.fullmatch(r'[a-zA-Z_]+',name):raise ValueError('UNEXPECTED_TABLE_NAME')
            tables[name]=db.execute('SELECT count(*) FROM '+name).fetchone()[0]
        return {'user_version':db.execute('PRAGMA user_version').fetchone()[0],'tables':tables}
    finally:db.close()
def check(root=ROOT):
    root=Path(root);before=json.loads((root/'research/v5_backup.json').read_text())['ledgers_before']
    paths=set(before)|{str(p.relative_to(root)).replace('\\','/') for p in (root/'monitoring/users').glob('*/reported.sqlite')}
    after={name:inspect(root/name) for name in sorted(paths)}
    return {'at':datetime.now(timezone.utc).isoformat(),'before':before,'after':after,'unchanged':before==after,'scope':'Owner and all guest reported ledgers plus risk/control.sqlite. Counts and PRAGMA user_version; no personal row contents. Services stopped during tests/demo. New idea tables are separate.'}
def write(root=ROOT):
    result=check(root);p=Path(root)/'research/V5_DATABASE_HYGIENE.json';p.write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    r=write();print(json.dumps(r,indent=2));raise SystemExit(not r['unchanged'])
