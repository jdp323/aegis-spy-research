"""Ephemeral loopback-only key import. Never print, log or retain plaintext keys."""
import json
import os
import secrets
import subprocess
import sys
import time
from http.client import HTTPConnection
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from data.credentials import NAMES, configured, save, validate
from data.key_verification import verify

def parse_keys(body):
    fields=parse_qs(body.decode('utf-8'),strict_parsing=True,keep_blank_values=True)
    if set(fields)!=set(NAMES) or any(len(values)!=1 for values in fields.values()):
        raise ValueError('INVALID_FIELDS')
    return validate({name:fields[name][0] for name in NAMES})

def parse_reddit(fields):
    from news.reddit import validate as reddit_validate
    names={'REDDIT_CLIENT_ID':'client_id','REDDIT_CLIENT_SECRET':'client_secret',
           'REDDIT_REFRESH_TOKEN':'refresh_token','REDDIT_USER_AGENT':'user_agent'}
    if set(fields)!=set(names)|{'REDDIT_ACCESS_APPROVED'} or any(len(v)!=1 for v in fields.values()) or fields['REDDIT_ACCESS_APPROVED'][0]!='yes':
        raise ValueError('APPROVED_READ_ACCESS_REQUIRED')
    return reddit_validate({**{dst:fields[src][0] for src,dst in names.items()},'access_approved':True})

def allowed_request(host,origin,expected,post=False):
    return host==expected and (origin=='http://'+expected if post else origin in (None,'http://'+expected))

class SetupServer(HTTPServer):
    def __init__(self,address,lifetime=600):
        if address[0]!='127.0.0.1':raise ValueError('LOOPBACK_REQUIRED')
        super().__init__(address,Handler)
        self.token=secrets.token_urlsafe(32)
        self.deadline=time.monotonic()+lifetime
        self.lifetime=lifetime
        self.used=False
        self.timeout=1

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(5)
    def log_message(self,*args):pass
    def reply(self,status,text,html=False):
        raw=text.encode('utf-8');self.send_response(status)
        self.send_header('Content-Type','text/html; charset=utf-8' if html else 'text/plain; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        # no-referrer makes native form POST Origin:null, defeating our exact-origin check.
        # Same-origin preserves the local POST origin while suppressing cross-origin referrers.
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; style-src 'unsafe-inline'")
        self.send_header('Connection','close');self.end_headers();self.wfile.write(raw)
    def valid(self,post=False):
        expected='127.0.0.1:'+str(self.server.server_port)
        if not allowed_request(self.headers.get('Host'),self.headers.get('Origin'),expected,post):
            self.reply(403,'Local origin required.');return False
        target=urlsplit(self.path)
        if target.path!='/setup/'+self.server.token or target.query:
            self.reply(404,'Not found.');return False
        if self.server.used or time.monotonic()>=self.server.deadline:
            self.reply(410,'Setup session ended.');return False
        return True
    def do_GET(self):
        if not self.valid():return
        self.reply(200,'''<!doctype html><html lang="en"><meta charset="utf-8"><title>AEGIS encrypted market-data setup</title>
<style>body{font:16px system-ui;max-width:580px;margin:40px auto;padding:20px}label{display:block;margin:18px 0}input{display:block;width:95%;padding:12px}button{padding:12px}</style>
<h1>AEGIS market-data setup</h1><p>This one-use page runs only on this computer. Alpaca API keys are encrypted with Windows DPAPI. They are never shown in logs or sent to Telegram.</p>
<p>AEGIS uses these keys for market data. A key may also carry Alpaca paper-trading permissions. Do not enter a password or use live-trading keys.</p>
<p>Before saving, this form checks the pair against Alpaca's read-only IEX data endpoint. A matching key ID and secret from the same generation are required.</p>
<h2>Optional FRED calendar</h2><p>Release dates only; no invented release times. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis. Read https://fred.stlouisfed.org/docs/api/terms_of_use.html before using.</p><form method="post" autocomplete="off"><label>FRED API key<input name="FRED_API_KEY" type="password" maxlength="32" required autocomplete="new-password"></label><button type="submit">Encrypt optional calendar key</button></form><h2>Questrade read-only market data</h2><p>Enter a refresh token from API Hub. Never enter a password. No personal account or order endpoints are used.</p><form method="post" autocomplete="off"><label>Refresh token<input name="QUESTRADE_REFRESH_TOKEN" type="password" required maxlength="2048" autocomplete="new-password"></label><button type="submit">Encrypt Questrade token</button></form><h2>Alpaca paper market data</h2><form method="post" autocomplete="off"><label>Paper API key ID<input name="APCA_API_KEY_ID" type="password" required maxlength="128" autocomplete="off"></label>
<label>Paper API secret<input name="APCA_API_SECRET_KEY" type="password" required maxlength="128" autocomplete="new-password"></label>
<button type="submit">Encrypt and connect market-data configuration</button></form>
<h2>Optional approved Reddit sentiment</h2>
<p>This form cannot grant Reddit approval. Use only a Reddit-approved application for this use case, with OAuth read access. A website login is insufficient. No raw posts or author names are retained; no model training uses Reddit content.</p>
<form method="post" autocomplete="off">
<label>Client ID<input name="REDDIT_CLIENT_ID" type="password" maxlength="512" required autocomplete="off"></label>
<label>Client secret<input name="REDDIT_CLIENT_SECRET" type="password" maxlength="512" required autocomplete="new-password"></label>
<label>OAuth refresh token (read scope)<input name="REDDIT_REFRESH_TOKEN" type="password" maxlength="512" required autocomplete="new-password"></label>
<label>User-Agent<input name="REDDIT_USER_AGENT" maxlength="128" placeholder="windows:AEGIS:1.0 (by /u/YOUR_USERNAME)" required></label>
<label><input name="REDDIT_ACCESS_APPROVED" type="checkbox" value="yes" required>I already have Reddit approval for this application's use case.</label>
<button type="submit">Encrypt approved Reddit configuration</button></form>
<p>This page expires after SESSION_MINUTES minutes. Existing configuration is never overwritten.</p></html>'''.replace('SESSION_MINUTES',str(max(1,int(self.server.lifetime/60)))),True)
    def do_POST(self):
        if self.headers.get('Content-Type','').split(';')[0]!='application/x-www-form-urlencoded' or self.headers.get('Transfer-Encoding'):
            self.reply(415,'Unsupported input.');return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8192:raise ValueError('BODY_LIMIT')
            self.connection.settimeout(5)
            raw=self.rfile.read(size)
            if len(raw)!=size:raise ValueError('INCOMPLETE_BODY')
            # Drain only a bounded body before closing rejected requests, so Windows
            # does not reset the connection and obscure the explicit error response.
            if not self.valid(True):return
            fields=parse_qs(raw.decode('utf-8'),strict_parsing=True,keep_blank_values=True)
            if any(k.startswith('REDDIT_') for k in fields):
                from news.reddit import save as reddit_save
                reddit_save(parse_reddit(fields));self.server.used=True
                self.reply(200,'Encrypted approved Reddit configuration saved. Restart AEGIS to verify OAuth read access. Configuration alone is not a verified sentiment sample. No secrets logged.');return
            if set(fields)=={'FRED_API_KEY'} and len(fields['FRED_API_KEY'])==1:
                from news.fred_calendar import save as fred_save
                fred_save(fields['FRED_API_KEY'][0]);self.server.used=True
                self.reply(200,'Encrypted optional FRED key saved. No release time is inferred. Restart AEGIS to collect date-only context. No order placed.');return
            if set(fields)=={'QUESTRADE_REFRESH_TOKEN'} and len(fields['QUESTRADE_REFRESH_TOKEN'])==1:
                from data.questrade_vault import Vault
                Vault().configure(fields['QUESTRADE_REFRESH_TOKEN'][0]);self.server.used=True
                self.reply(200,'Encrypted Questrade refresh token saved. Restart AEGIS, then run python -m data.questrade_check. Freshness and entitlement remain unverified. No order was placed.');return
            keys=parse_keys(raw)
            access=verify(keys)
            if access!='AUTHENTICATED_IEX':
                self.reply(400,'Alpaca rejected the key/secret pair (401). Enter the matching paper key ID and secret from the same generation. Nothing saved.' if access=='AUTHENTICATION_REJECTED' else 'Alpaca data access could not be verified. Nothing saved. Check connectivity or data access and try again.');return
            save(keys)
            self.server.used=True
            self.reply(200,'Alpaca IEX authentication verified. Encrypted market-data configuration saved. SIP/OPRA access and live quote freshness still need verification. No order was placed. Restart AEGIS to connect the feeds.')
        except Exception:
            self.reply(400,'Setup was not saved or existing configuration was preserved. No keys logged.')

def main(lifetime=3600,token=None):
    # Existing Alpaca keys do not prevent the separate Questrade token setup.
    with SetupServer(('127.0.0.1',8769),lifetime=lifetime) as server:
        if token is not None:server.token=token
        print(json.dumps({'setup_url':'http://127.0.0.1:8769/setup/'+server.token,'expires_in_seconds':lifetime}),flush=True)
        while not server.used and time.monotonic()<server.deadline:server.handle_request()
        print('LOCAL_SETUP_SAVED' if server.used else 'LOCAL_SETUP_EXPIRED',flush=True)

def launch():
    """Bounded hidden child, independent of a tool terminal; no URL/credential logs."""
    # Existing Alpaca keys do not prevent the separate Questrade token setup.
    # Never take over an existing listener or expose its session capability.
    import socket
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',8769))==0:raise RuntimeError('SETUP_ALREADY_RUNNING')
    token=secrets.token_urlsafe(32);env=dict(os.environ);env['AEGIS_LOCAL_SETUP_TOKEN']=token
    flags=(subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW) if os.name=='nt' else 0
    process=subprocess.Popen([sys.executable,'-m','data.local_setup','--serve'],
        cwd=str(Path(__file__).resolve().parents[1]),env=env,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=flags,start_new_session=os.name!='nt')
    target='/setup/'+token
    for _ in range(30):
        if process.poll() is not None:raise RuntimeError('SETUP_START_FAILED')
        try:
            client=HTTPConnection('127.0.0.1',8769,timeout=.5)
            try:
                client.request('GET',target);response=client.getresponse();body=response.read()
                if response.status==200 and b'AEGIS market-data setup' in body:
                    print(json.dumps({'setup_url':'http://127.0.0.1:8769'+target,'expires_in_seconds':3600,'pid':process.pid}),flush=True)
                    return
            finally:client.close()
        except OSError:pass
        time.sleep(.1)
    raise RuntimeError('SETUP_START_TIMEOUT')

if __name__=='__main__':
    try:
        if sys.argv[1:]==['--launch']:launch()
        elif sys.argv[1:] in ([],['--serve']):main(token=os.environ.pop('AEGIS_LOCAL_SETUP_TOKEN',None))
        else:raise RuntimeError('INVALID_ARGUMENTS')
    except Exception:print('LOCAL_SETUP_UNAVAILABLE. No keys logged.');raise SystemExit(1)
