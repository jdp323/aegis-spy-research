"""Optional external liveness ping. Never logs endpoint, headers or response bodies."""
from urllib.parse import urlparse
from datetime import datetime,timezone
import urllib.request
from data.models import stamp
def validate_url(url):
 if url=='':return url
 p=urlparse(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('HEARTBEAT_HTTPS_REQUIRED')
 return url
def tick(store,config,session,now,transport=None):
 url=validate_url(config.get('heartbeat_url',''))
 if not url or not session['active']:return {'state':'DISABLED' if not url else 'OUTSIDE_SESSION'}
 old=store.get('external_heartbeat')
 if old and (now-stamp(old['at'])).total_seconds()<300:return old
 def send(url):
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AEGIS-liveness/1.0'}),timeout=2) as response:response.read(1)
 status={'at':now.isoformat(),'state':'ATTEMPT_RESERVED'};store.put('external_heartbeat',status)
 try:(transport or send)(url);status['state']='PING_ACCEPTED'
 except Exception:status['state']='PING_FAILED'
 store.put('external_heartbeat',status);return status
