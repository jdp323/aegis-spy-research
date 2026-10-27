"""Publication guard. Inspect Git contents; never print matching secret text."""
import argparse,json,re,subprocess,sys
from pathlib import Path
from core.storage import ROOT

BLOCK_PARTS={'.private','.venv','.vendor','.shadow-model','runtime','logs','daily_reports','users','inbox','outbox','demo_sessions','premarket_cache','premarket_authorized_cache','public_cache','closing_cache','__pycache__'}
BLOCK_NAMES={'access.json','telegram.json','news_calendar.json','risk_state.json','system_state.json','demo_state.json'}
ALLOWED_JSON={'config/upgrade.json','config/news_calendar.example.json','config/telegram.example.json','data/tsx_calendar.json','research/v5_requirements.json','research/combined_requirements.json'}
SECRET_PATTERNS=[('telegram token',re.compile(rb'(?<![A-Za-z0-9])[0-9]{7,12}:[A-Za-z0-9_-]{30,}')),
 ('OpenAI-style key',re.compile(rb'(?<![A-Za-z0-9])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}')),
 ('GitHub token',re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})')),
 ('private key',re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
 ('owner machine path',re.compile(rb'C:[/\\]Users[/\\]Auto[/\\]',re.I)),
 ('credential assignment',re.compile(rb'''(?i)["']?(?:APCA_API_KEY_ID|APCA_API_SECRET_KEY)["']?\s*[:=]\s*["'][A-Za-z0-9_-]{8,}["']'''))]

def path_problem(name):
    path=Path(name);parts=set(path.parts);leaf=path.name
    if parts&BLOCK_PARTS or leaf in BLOCK_NAMES:return 'private/runtime path'
    if leaf.startswith('.env') and leaf!='.env.example':return 'environment credential file'
    if re.search(r'\.(?:dpapi|sqlite(?:3)?|db)(?:-|$|\.)',leaf,re.I) or leaf.endswith(('-wal','-shm','.pyc','.zip','.bak')):return 'private/binary record'
    if leaf.startswith(('account_snapshot','VERIFICATION_PACKET','COMMAND_VERIFICATION_','SCHEDULE_VERIFICATION_')):return 'unsanitized generated evidence'
    if path.suffix=='.json' and name not in ALLOWED_JSON:return 'unapproved JSON payload'
    return None

def inspect(entries,changed=None,require_report=True):
    failures=[]
    for name,body in entries.items():
        reason=path_problem(name)
        if reason:failures.append({'path':name,'reason':reason});continue
        for label,pattern in SECRET_PATTERNS:
            if pattern.search(body):failures.append({'path':name,'reason':label})
        if b'\x00' in body:failures.append({'path':name,'reason':'unexpected binary file'})
    changed=set(entries if changed is None else changed)
    if require_report and changed:
        reports=[p for p in changed if p.startswith('reports/updates/') and p.endswith('.md') and p in entries]
        if not reports:failures.append({'path':'reports/updates/','reason':'every publication needs a new update report'})
        setup_change=any(p=='requirements-upgrade.txt' or p.startswith(('config/','core/runtime_paths','monitoring/runtime','monitoring/vault','monitoring/bot_identity','ops/setup','ops/supervisor')) or p.endswith(('.cmd','.ps1')) for p in changed)
        if setup_change and 'SETUP.md' not in changed:failures.append({'path':'SETUP.md','reason':'setup-affecting changes require updated instructions'})
        for p in reports:
            text=entries[p].decode('utf-8',errors='replace')
            for section in ('Changes','Verification','Limitations','Setup impact'):
                if section.lower() not in text.lower():failures.append({'path':p,'reason':'report missing '+section})
    return failures

def git(root,*args):
    r=subprocess.run(['git','-C',str(root),*args],capture_output=True)
    if r.returncode:raise RuntimeError('Git unavailable or command failed')
    return r.stdout

def git_entries(root,ref=None):
    raw=git(root,'ls-tree','-r','-z',ref) if ref else git(root,'ls-files','--stage','-z')
    rows=[]
    for record in raw.split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);fields=metadata.split()
        if fields[0] not in (b'100644',b'100755'):raise RuntimeError('Symlinks and submodules are not publishable')
        if ref:
            if fields[1]!=b'blob':raise RuntimeError('Unsupported Git object')
            sha=fields[2]
        else:
            if fields[2]!=b'0':raise RuntimeError('Resolve index conflicts before publication')
            sha=fields[1]
        rows.append((name.decode('utf-8'),sha))
    if not rows:return {}
    proc=subprocess.run(['git','-C',str(root),'cat-file','--batch'],input=b'\n'.join(sha for _,sha in rows)+b'\n',capture_output=True)
    if proc.returncode:raise RuntimeError('Git content read failed')
    result={};offset=0
    for name,_ in rows:
        end=proc.stdout.index(b'\n',offset);header=proc.stdout[offset:end].split()
        if len(header)!=3 or header[1]!=b'blob':raise RuntimeError('Unexpected Git content')
        size=int(header[2]);offset=end+1;result[name]=proc.stdout[offset:offset+size];offset+=size+1
    return result

def collect(root,base=None,working=False):
    root=Path(root)
    if working:
        if (root/'.git').exists():names=git(root,'ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0')
        else:names=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and not set(p.relative_to(root).parts)&(BLOCK_PARTS|{'.git'}) and p.name not in BLOCK_NAMES and not p.name.endswith('.pyc')]
        return {n:(root/n).read_bytes() for n in names if n and (root/n).is_file()},[],False
    if base:
        entries=git_entries(root,'HEAD')
        changed=git(root,'diff','--name-only','-z',base,'HEAD').decode().split('\0')
        old=set(git(root,'ls-tree','-r','--name-only','-z',base).decode().split('\0'))
        changed=[n for n in changed if n and not(n.startswith('reports/updates/') and n in old)]
        return entries,changed,True
    entries=git_entries(root)
    changed=git(root,'diff','--cached','--name-only','-z').decode().split('\0')
    added=set(git(root,'diff','--cached','--diff-filter=A','--name-only','-z').decode().split('\0'))
    changed=[n for n in changed if n and not(n.startswith('reports/updates/') and n not in added)]
    return entries,changed,True

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base');parser.add_argument('--working-tree',action='store_true');args=parser.parse_args(argv)
    try:
        entries,changed,require=collect(ROOT,args.base,args.working_tree);failures=inspect(entries,changed,require)
        print(json.dumps({'status':'FAIL' if failures else 'PASS','files_scanned':len(entries),'failures':failures},indent=2));return bool(failures)
    except Exception:
        print('RELEASE_GUARD_UNAVAILABLE: publication blocked; no sensitive values printed.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
