"""Prepare pinned optional public model assets; no API key, no live promotion."""
import argparse,json,hashlib,subprocess,sys,os,urllib.request,venv
from pathlib import Path
from core.storage import ROOT
from research.shadow_forecast import MODEL,MODEL_REVISION,TOKENIZER,TOKENIZER_REVISION,CODE_REVISION

def fetch(url,target,maximum):
    target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.download')
    try:
        # Uses certificate verification. No insecure TLS fallback.
        with urllib.request.urlopen(url,timeout=30) as r,temporary.open('wb') as f:
            count=0
            while chunk:=r.read(65536):
                count+=len(chunk)
                if count>maximum:raise ValueError('PUBLIC_ASSET_TOO_LARGE')
                f.write(chunk)
    except urllib.error.URLError:
        if os.name!='nt':raise
        curl=Path(os.environ['SystemRoot'])/'System32/curl.exe'
        r=subprocess.run([str(curl),'--fail','--location','--silent','--show-error','--max-time','60','--max-filesize',str(maximum),'--output',str(temporary),url],capture_output=True,timeout=65)
        if r.returncode:raise RuntimeError('VERIFIED_PUBLIC_ASSET_DOWNLOAD_FAILED')
    if temporary.stat().st_size>maximum:raise ValueError('PUBLIC_ASSET_TOO_LARGE')
    temporary.replace(target)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets-only',action='store_true');args=p.parse_args();home=ROOT/'.shadow-model';home.mkdir(exist_ok=True)
    files={};metadata={'model_revision':MODEL_REVISION,'tokenizer_revision':TOKENIZER_REVISION,'code_revision':CODE_REVISION,'license':'MIT; notices retained with downloaded assets','training_independence':'exact checkpoint training dates/overlap not established; future evaluation required'}
    for relative in ('model/__init__.py','model/kronos.py','model/module.py','LICENSE'):
        target=home/'code'/relative
        fetch('https://raw.githubusercontent.com/shiyu-coder/Kronos/'+CODE_REVISION+'/'+relative,target,2*1024*1024)
        files[target.relative_to(home).as_posix()]=hashlib.sha256(target.read_bytes()).hexdigest()
    for folder,repo,revision in [('model',MODEL,MODEL_REVISION),('tokenizer',TOKENIZER,TOKENIZER_REVISION)]:
        # Pinned repository Git revision; individual content hashes retained.
        for name in ('config.json','README.md','model.safetensors'):
            target=home/folder/name;fetch('https://huggingface.co/'+repo+'/resolve/'+revision+'/'+name,target,128*1024*1024)
            with target.open('rb') as f:files[target.relative_to(home).as_posix()]=hashlib.file_digest(f,'sha256').hexdigest()
    metadata['files']=files;(home/'ASSETS.json').write_text(json.dumps(metadata,indent=2))
    if not args.assets_only:
        from ops.shadow_worker import available_memory,MINIMUM_FREE_BYTES,environment
        if available_memory()<MINIMUM_FREE_BYTES:raise RuntimeError('INSUFFICIENT_MEMORY_HEADROOM; assets retained; environment not installed')
        venv.EnvBuilder(with_pip=True).create(home/'venv');py=home/('venv/Scripts/python.exe' if os.name=='nt' else 'venv/bin/python')
        subprocess.run([str(py),'-m','pip','install','--index-url','https://download.pytorch.org/whl/cpu','torch==2.8.0+cpu'],check=True,env=environment(),timeout=600)
        subprocess.run([str(py),'-m','pip','install','-r',str(ROOT/'requirements-shadow.txt')],check=True,env=environment(),timeout=300)
    print(json.dumps({'assets_prepared':True,'environment_installed':not args.assets_only,'files':files}))
if __name__=='__main__':main()
