"""Local backups; SQLite online backup captures WAL safely. Restore into a new folder."""
import hashlib,json,sqlite3,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
from core.storage import ROOT
def backup(destination,root=ROOT):
    root=Path(root).resolve();destination=Path(destination).resolve()
    if destination==root or root in destination.parents:raise ValueError('Backup must be outside project')
    destination.mkdir(parents=True,exist_ok=False);manifest={}
    for p in root.rglob('*'):
        rel=p.relative_to(root)
        if p.is_symlink() or any(x in ('.vendor','.venv','__pycache__','.git') for x in rel.parts) or not p.is_file() or p.name.endswith(('-wal','-shm','.lock','.pyc','.pid')):continue
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix in ('.sqlite','.db'):
            src=sqlite3.connect('file:'+p.as_posix()+'?mode=ro',uri=True);dst=sqlite3.connect(target)
            try:src.backup(dst);assert dst.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            finally:src.close();dst.close()
        else:shutil.copy2(p,target)
        manifest[str(rel)]=hashlib.sha256(target.read_bytes()).hexdigest()
    (destination/'BACKUP_MANIFEST.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'files':manifest},indent=2));return len(manifest)
def restore(source,destination):
    source=Path(source).resolve();destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Restore requires a new empty destination path')
    manifest=json.loads((source/'BACKUP_MANIFEST.json').read_text())
    for rel,digest in manifest['files'].items():
        p=(source/rel).resolve()
        if source not in p.parents or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('BACKUP_INTEGRITY_FAILED')
    destination.mkdir(parents=True)
    for rel in manifest['files']:
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,target)
    return len(manifest['files'])
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['backup','restore']);p.add_argument('path');p.add_argument('--destination');a=p.parse_args()
    print(backup(a.path) if a.mode=='backup' else restore(a.path,a.destination))
