"""Runs ONLY in the separate optional model environment, fully offline."""
import os,sys,json,time,hashlib,random,math
from pathlib import Path
from datetime import datetime,timezone

def main():
    request=json.loads(sys.stdin.read(524288));start=time.monotonic()
    home=Path(sys.argv[1]).resolve();manifest=json.loads((home/'ASSETS.json').read_text())
    from research.shadow_forecast import MODEL_REVISION,TOKENIZER_REVISION,CODE_REVISION,FEATURES
    if (manifest['model_revision'],manifest['tokenizer_revision'],manifest['code_revision'])!=(MODEL_REVISION,TOKENIZER_REVISION,CODE_REVISION):raise ValueError('PINNED_ASSETS_REQUIRED')
    for name,digest in manifest['files'].items():
        p=(home/name).resolve()
        if home not in p.parents:raise ValueError('ASSET_PATH_INVALID')
        with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=digest:raise ValueError('ASSET_HASH_MISMATCH')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled',HF_HUB_DISABLE_TELEMETRY='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    sys.path.insert(0,str(home/'code'))
    import numpy as np,pandas as pd,torch
    from model import Kronos,KronosTokenizer,KronosPredictor
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    tokenizer=KronosTokenizer.from_pretrained(str(home/'tokenizer'),local_files_only=True);model=Kronos.from_pretrained(str(home/'model'),local_files_only=True)
    tokenizer.eval();model.eval();predictor=KronosPredictor(model,tokenizer,device='cpu',max_context=512)
    df=pd.DataFrame(request['input_rows']);x=pd.to_datetime(df.pop('start_at'),utc=True).dt.tz_convert('America/New_York').dt.tz_localize(None);y=pd.Series(pd.to_datetime(request['future_starts'],utc=True)).dt.tz_convert('America/New_York').dt.tz_localize(None)
    paths=[]
    for seed in request['seeds']:
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        with torch.inference_mode():pred=predictor.predict(df=df[list(FEATURES)],x_timestamp=x,y_timestamp=y,pred_len=len(y),T=request['temperature'],top_k=request['top_k'],top_p=request['top_p'],sample_count=1,verbose=False)
        bars=[dict(zip(FEATURES,map(float,row)),start_at=t) for t,row in zip(request['future_starts'],pred[list(FEATURES)].to_numpy())]
        paths.append({'seed':seed,'bars':bars})
    result={'request_id':request['id'],'paths':paths,'runtime_seconds':time.monotonic()-start,'device':'cpu','threads':1,'model_revision':MODEL_REVISION,'tokenizer_revision':TOKENIZER_REVISION,'asset_hashes':manifest['files'],'dependency_versions':{'torch':torch.__version__,'numpy':np.__version__,'pandas':pd.__version__},'model_generated':True}
    print(json.dumps(safe_raw(result),allow_nan=False))

def safe_raw(value):
    # Retain invalid outputs explicitly; these markers fail numerical validation.
    if isinstance(value,float) and not math.isfinite(value):return 'MODEL_NONFINITE_'+str(value).upper()
    if isinstance(value,dict):return {k:safe_raw(v) for k,v in value.items()}
    if isinstance(value,list):return [safe_raw(v) for v in value]
    return value
if __name__=='__main__':main()
