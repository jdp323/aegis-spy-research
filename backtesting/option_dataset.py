"""Offline historical SPY quote inspection; structural checks never validate an edge.

No download, credential access, trading, strategy promotion or position updates.
Manifest assertions are not independent evidence of data provenance/coverage.
"""
import hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
from core.storage import ROOT
from core.sessions import ET
from data.models import stamp,finite
from options.ledger import contract

VERSION='spy-option-quotes-v1'
MAX_BYTES=64*1024*1024

def inspect(manifest_path=None,now=None):
    now=now or datetime.now(timezone.utc)
    path=Path(manifest_path or ROOT/'research/option_dataset_manifest.json')
    report={'schema_version':VERSION,'checked_at':now.isoformat(),'status':'UNAVAILABLE','structural_valid':False,'provenance':'UNVERIFIED','coverage':'UNVERIFIED','strategy_validated':False,'live_ready':False,'action':'NO TRADE','reasons':[],'quote_rows':0}
    try:
        if not path.exists():raise ValueError('HISTORICAL_OPTION_DATASET_UNAVAILABLE')
        if path.stat().st_size>65536:raise ValueError('MANIFEST_TOO_LARGE')
        manifest=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(manifest,dict) or manifest.get('schema_version')!=VERSION or manifest.get('underlying')!='SPY':raise ValueError('MANIFEST_SCHEMA_INVALID')
        provider=manifest.get('provider')
        if not isinstance(provider,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',provider):raise ValueError('PROVIDER_REQUIRED')
        feed=manifest.get('feed')
        if feed not in ('OPRA','SYNTHETIC'):raise ValueError('NON_OPRA_OPTION_QUOTES_REJECTED')
        source=urlsplit(manifest.get('source_url',''))
        if source.scheme!='https' or not source.hostname or source.username or source.password or source.query or source.fragment:raise ValueError('SAFE_SOURCE_URL_REQUIRED')
        retrieved=stamp(manifest['retrieved_at'])
        if retrieved>now:raise ValueError('FUTURE_RETRIEVAL_TIMESTAMP')
        filename=manifest.get('data_file')
        if not isinstance(filename,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}\.jsonl',filename):raise ValueError('LOCAL_DATA_FILE_REQUIRED')
        folder=path.parent.resolve();data=(folder/filename).resolve()
        if data.parent!=folder or data.is_symlink():raise ValueError('DATA_PATH_ESCAPE')
        if data.stat().st_size>MAX_BYTES:raise ValueError('DATASET_TOO_LARGE')
        body=data.read_bytes()
        if len(body)>MAX_BYTES:raise ValueError('DATASET_TOO_LARGE')
        digest=hashlib.sha256(body).hexdigest()
        if manifest.get('sha256')!=digest:raise ValueError('DATASET_HASH_MISMATCH')
        report.update(provider=provider,feed=feed,source_url=manifest['source_url'],data_sha256=digest)
        previous={};first=None;last=None;contracts=set();count=0
        for line in body.decode('utf-8').splitlines():
            if not line.strip():continue
            row=json.loads(line)
            if not isinstance(row,dict) or row.get('provider')!=provider or row.get('feed')!=feed or row.get('data_type')!='option_quote':raise ValueError('QUOTE_PROVENANCE_FIELDS_MISMATCH')
            symbol=row.get('symbol');spec=contract(symbol)
            source_time=stamp(row['source_timestamp']);received=stamp(row['received_timestamp'])
            if source_time>received or received>retrieved:raise ValueError('QUOTE_TIMESTAMPS_INVALID')
            if source_time.astimezone(ET).date().isoformat()>spec['expiry']:raise ValueError('QUOTE_AFTER_EXPIRATION')
            if symbol in previous and source_time<=previous[symbol]:raise ValueError('DUPLICATE_OR_OUT_OF_ORDER_QUOTE')
            bid=row.get('bid');ask=row.get('ask')
            if not finite(bid) or not finite(ask) or not 0<=bid<=ask or ask<=0:raise ValueError('OPTION_BID_ASK_INVALID')
            for key in ('bid_size','ask_size'):
                if type(row.get(key)) is not int or row[key]<0:raise ValueError('OPTION_QUOTE_SIZE_INVALID')
            previous[symbol]=source_time;contracts.add(symbol);count+=1
            first=source_time if first is None else min(first,source_time)
            last=source_time if last is None else max(last,source_time)
        if count<2:raise ValueError('INSUFFICIENT_QUOTE_ROWS')
        if type(manifest.get('row_count')) is not int or manifest['row_count']!=count:raise ValueError('ROW_COUNT_MISMATCH')
        report.update(status='SYNTHETIC_ONLY' if feed=='SYNTHETIC' else 'STRUCTURALLY_INSPECTED_ONLY',structural_valid=True,quote_rows=count,contract_count=len(contracts),first_source_timestamp=first.isoformat(),last_source_timestamp=last.isoformat(),reasons=['PROVENANCE_AND_COVERAGE_NOT_INDEPENDENTLY_VERIFIED','REALISTIC_OPTIONS_BACKTEST_AND_PROSPECTIVE_EVIDENCE_REQUIRED'])
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError) as error:
        report['status']='UNAVAILABLE' if not path.exists() else 'REJECTED'
        report['reasons']=[str(error) if isinstance(error,ValueError) and re.fullmatch(r'[A-Z_]+',str(error)) else 'DATASET_SCHEMA_OR_IO_INVALID']
    return report

if __name__=='__main__':print(json.dumps(inspect(sys.argv[1] if len(sys.argv)>1 else None),indent=2))
