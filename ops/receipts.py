"""Owner-local receipt review. Default read-only; confirmations append separately."""
import argparse,json,hashlib
from datetime import datetime,timezone
from core.storage import ROOT
from data.models import stamp
ALLOWED={'PENDING_OR_UNCERTAIN','UNCERTAIN_AFTER_SEND','FAILED_NOT_ACCEPTED'}
def listing(root=ROOT):
    directory=root/'logs/notifications';result=[]
    confirmations=directory/'owner_confirmations.jsonl';confirmed=set()
    if confirmations.exists():
        for line in confirmations.read_text().splitlines():
            try:confirmed.add(json.loads(line)['receipt_hash'])
            except (ValueError,KeyError):pass
    for p in directory.rglob('*.json') if directory.exists() else []:
        try:
            d=json.loads(p.read_text());role='guest' if 'guests' in p.relative_to(directory).parts else 'owner';status=d.get('status','PENDING_OR_UNCERTAIN');ident=hashlib.sha256(p.relative_to(directory).as_posix().encode()+b'\0'+p.read_bytes()).hexdigest()
            if ident in confirmed:status='CONFIRMED_BY_OWNER'
            if status not in ALLOWED:continue
            result.append({'receipt_hash':ident,'age_seconds':(datetime.now(timezone.utc)-stamp(d['created_at'])).total_seconds(),'kind':d.get('kind','UNKNOWN'),'role':role,'status':status,'failure_class':d.get('failure_class','UNAVAILABLE')})
        except (OSError,ValueError,KeyError,TypeError):continue
    return sorted(result,key=lambda x:-x['age_seconds'])
def confirm(receipt_hash,root=ROOT):
    row=next((r for r in listing(root) if r['receipt_hash']==receipt_hash),None)
    if row is None or row['role']!='owner':raise ValueError('ONLY_OWNER_VISIBLE_RECEIPT_CAN_BE_CONFIRMED')
    folder=root/'logs/notifications';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'owner_confirmations.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'receipt_hash':receipt_hash,'status':'CONFIRMED_BY_OWNER','scope':'Owner attests seeing the message; no resend and no guest confirmation'})+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--confirm-owner',metavar='RECEIPT_HASH');a=p.parse_args()
    if a.confirm_owner:confirm(a.confirm_owner)
    print(json.dumps(listing(),indent=2))
if __name__=='__main__':main()
