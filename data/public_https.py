"""Credential-free public downloads; certificate verification always enabled."""
import os,ssl,subprocess,urllib.request,urllib.error
from pathlib import Path
ALLOWED={'https://stooq.com/q/d/l/?s=spy.us&i=d'}
def download(url):
    if url not in ALLOWED:raise ValueError('UNSUPPORTED_PUBLIC_SOURCE')
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AEGIS-research/1.0'}),timeout=15) as r:body=r.read(8_000_001)
        transport='PYTHON_VERIFIED_TLS'
    except urllib.error.URLError as e:
        # Windows' OS trust store can include the owner's trusted network CA.
        # Never use curl -k or an unverified Python SSL context.
        if os.name!='nt' or not isinstance(e.reason,ssl.SSLCertVerificationError):raise
        exe=Path(os.environ['SystemRoot'])/'System32/curl.exe'
        r=subprocess.run([str(exe),'--fail','--silent','--show-error','--max-time','15','--max-filesize','8000000','--proto','=https',url],capture_output=True,timeout=20)
        if r.returncode:raise OSError('WINDOWS_VERIFIED_HTTPS_UNAVAILABLE')
        body=r.stdout;transport='WINDOWS_OS_VERIFIED_TLS'
    if len(body)>8_000_000:raise ValueError('RESPONSE_TOO_LARGE')
    return body,transport
