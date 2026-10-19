"""Authorized read-only Reddit adapter; bounded samples, no raw content retention.

No anonymous JSON/RSS bypass. Missing OAuth approval means not configured.
Public user text is untrusted evidence, not an instruction or a trading signal.
"""
import json,re,urllib.request,urllib.error,urllib.parse
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from core.sessions import ET
from data.models import stamp,finite
from news.market_outlook import language,shares,lean,clean,ratio_line

from core.runtime_paths import private_directory
PRIVATE=private_directory()/'reddit.dpapi'
FIELDS={'client_id','client_secret','refresh_token','user_agent','access_approved'}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('REDDIT_REDIRECT_REJECTED')
def validate(c):
    if not isinstance(c,dict) or set(c)!=FIELDS or c['access_approved'] is not True:raise ValueError('APPROVED_READ_ACCESS_REQUIRED')
    for k in ('client_id','client_secret','refresh_token'):
        if not isinstance(c[k],str) or not 8<=len(c[k])<=512 or not re.fullmatch(r'[A-Za-z0-9._~+/-]+',c[k]):raise ValueError('INVALID_REDDIT_CONFIG')
    if not isinstance(c['user_agent'],str) or not re.fullmatch(r'windows:AEGIS:[A-Za-z0-9.-]+ \(by /u/[A-Za-z0-9_-]{3,32}\)',c['user_agent']):raise ValueError('DESCRIPTIVE_REDDIT_USER_AGENT_REQUIRED')
    return c
def credentials():
    if not PRIVATE.is_file():return None
    from monitoring.vault import transform
    try:return validate(json.loads(transform(PRIVATE.read_bytes(),True)))
    except Exception:raise RuntimeError('REDDIT_ENCRYPTED_CONFIG_UNREADABLE') from None

class RedditProvider:
    def __init__(self,transport=None,config_loader=credentials):
        self.transport=transport;self.config_loader=config_loader;self.token=None;self.expires=None;self.retry_at=None
    def request(self,path,params,c,now):
        if self.transport:return self.transport(path,params)
        import base64
        if not self.token or now>=self.expires:
            data=urllib.parse.urlencode({'grant_type':'refresh_token','refresh_token':c['refresh_token']}).encode()
            authorization=base64.b64encode((c['client_id']+':'+c['client_secret']).encode()).decode()
            req=urllib.request.Request('https://www.reddit.com/api/v1/access_token',data=data,headers={'User-Agent':c['user_agent'],'Authorization':'Basic '+authorization})
            raw=self.fetch(req)
            if raw.get('token_type','').lower()!='bearer' or not isinstance(raw.get('access_token'),str) or not raw['access_token'] or type(raw.get('expires_in')) is not int or raw['expires_in']<60:raise ValueError('REDDIT_AUTH_INVALID')
            if not {'read'}.issubset(set(str(raw.get('scope','')).split())) and raw.get('scope')!='*':raise ValueError('READ_SCOPE_REQUIRED')
            self.token=raw['access_token'];self.expires=now+timedelta(seconds=min(raw['expires_in'],3600)-30)
        req=urllib.request.Request('https://oauth.reddit.com'+path+'?'+urllib.parse.urlencode(params),headers={'User-Agent':c['user_agent'],'Authorization':'Bearer '+self.token,'Accept':'application/json'})
        return self.fetch(req)
    @staticmethod
    def fetch(req):
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=6) as response:
            if urllib.parse.urlsplit(response.geturl()).hostname!=urllib.parse.urlsplit(req.full_url).hostname:raise ValueError('REDDIT_REDIRECT_REJECTED')
            body=response.read(1024*1024+1)
            remaining=response.headers.get('X-Ratelimit-Remaining')
            if remaining is not None and float(remaining)<=0:raise urllib.error.HTTPError(req.full_url,429,'rate limit',response.headers,None)
        if len(body)>1024*1024:raise ValueError('REDDIT_RESPONSE_LIMIT')
        return json.loads(body)
    def collect(self,now=None):
        now=now or datetime.now(timezone.utc)
        out={'provider':'reddit-oauth','source_url':'https://www.reddit.com/r/wallstreetbets/top/?t=day','fetched_at':now.isoformat(),
             'quality':'FEED_NOT_CONFIGURED','reason':'Authorized Reddit API access is not configured; no posts or comments analyzed.',
             'bias':'UNAVAILABLE','support':shares([]),'raw_content_stored':False,'representative_sample':False,'coverage_complete':False,
             'posts_examined':0,'relevant_posts':0,'comments_examined':0,'relevant_comments':0,'topics':[],'threads':[]}
        try:
            c=self.config_loader()
            if not c:return out
            validate(c)
            if self.retry_at and now<self.retry_at:return {**out,'quality':'FEED_DISCONNECTED','reason':'Reddit access/rate-limit cooldown active.'}
            listing=self.request('/r/wallstreetbets/top',{'t':'day','limit':25,'raw_json':1},c,now)
            posts=self.children(listing,25,'t3');sample=[];threads=[];seen=set();topics=set()
            for p in posts:
                self.valid_record(p,now)
                if p.get('subreddit','').lower()!='wallstreetbets':raise ValueError('SUBREDDIT_MISMATCH')
                id=p['id']
                if id in seen:continue
                seen.add(id);out['posts_examined']+=1
                if p.get('removed_by_category') or p.get('author') in ('[deleted]',None):continue
                text=clean(p.get('title',''),200)+' '+clean(p.get('selftext',''),800)
                v=language(text,social=True)
                if v['direction']=='IRRELEVANT':continue
                sample.append(v['direction']);out['relevant_posts']+=1
                topics.update(self.topics(text))
                threads.append({'id':id,'url':'https://www.reddit.com/r/wallstreetbets/comments/'+id+'/',
                    'score':p['score'],'comment_count':p.get('num_comments',0),'direction':v['direction']})
            # Top listing order is retained; at most three relevant threads,
            # at most20 visible top comments each. Never fetch "more" recursively.
            for thread in threads[:3]:
                raw=self.request('/r/wallstreetbets/comments/'+thread['id'],{'sort':'top','limit':20,'depth':1,'raw_json':1},c,now)
                if not isinstance(raw,list) or len(raw)!=2:raise ValueError('COMMENT_CONTAINER_INVALID')
                parent=self.children(raw[0],1,'t3')
                if len(parent)!=1 or parent[0].get('id')!=thread['id'] or parent[0].get('subreddit','').lower()!='wallstreetbets':raise ValueError('COMMENT_PARENT_MISMATCH')
                for p in self.children(raw[1],20,'t1'):
                    self.valid_record(p,now)
                    if p.get('link_id')!='t3_'+thread['id'] or p.get('subreddit','').lower()!='wallstreetbets':raise ValueError('COMMENT_LINK_MISMATCH')
                    if p['id'] in seen:continue
                    seen.add(p['id']);out['comments_examined']+=1
                    if p.get('author') in ('[deleted]',None) or p.get('body') in ('[removed]','[deleted]'):continue
                    text=clean(p.get('body',''),1000);v=language(text,social=True)
                    # Comments need their own market context, not inferred from a thread.
                    if v['direction']=='IRRELEVANT':continue
                    out['relevant_comments']+=1;sample.append(v['direction']);topics.update(self.topics(text))
            s=shares(sample);out.update(quality='DATA_OK',reason='BOUNDED_AUTHORIZED_SAMPLE',bias=lean(s),support=s,
                                       threads=threads[:3],topics=sorted(topics),sample_definition='Top25 daily posts; first3 relevant threads, up to20 top comments each. Equal text votes; upvotes do not weight direction.')
        except urllib.error.HTTPError as e:
            delay=3600
            if e.code==429:
                try:delay=max(60,min(3600,float(e.headers.get('Retry-After') or e.headers.get('X-Ratelimit-Reset') or 60)))
                except (TypeError,ValueError):pass
            self.retry_at=now+timedelta(seconds=delay);out.update(quality='FEED_DISCONNECTED',reason='REDDIT_HTTP_'+str(e.code));self.token=None
        except Exception:out.update(quality='DATA_INCOMPLETE',reason='REDDIT_UNAVAILABLE_OR_INVALID')
        # Any partial failure suppresses the entire sentiment calculation.
        if out['quality']!='DATA_OK':out.update(bias='UNAVAILABLE',support=shares([]),threads=[],topics=[])
        return out
    @staticmethod
    def children(raw,limit,kind):
        if not isinstance(raw,dict) or raw.get('kind')!='Listing' or not isinstance(raw.get('data'),dict) or not isinstance(raw['data'].get('children'),list) or len(raw['data']['children'])>limit:raise ValueError('LISTING_INVALID')
        children=raw['data']['children']
        if any(not isinstance(p,dict) or p.get('kind') not in (kind,'more') or not isinstance(p.get('data'),dict) for p in children):raise ValueError('LISTING_RECORD_INVALID')
        return [p['data'] for p in children if p['kind']==kind]
    @staticmethod
    def valid_record(p,now):
        if not re.fullmatch('[a-z0-9]{1,12}',p.get('id','')) or not finite(p.get('created_utc')) or not 0<=now.timestamp()-p['created_utc']<=48*3600 or type(p.get('score')) is not int:raise ValueError('RECORD_INVALID')
    @staticmethod
    def topics(text):
        from news.market_outlook import TOPICS
        return [k for k,p in TOPICS.items() if re.search(p,text,re.I)]

def fresh_summary(raw,now=None):
    now=now or datetime.now(timezone.utc);out=dict(raw or {'quality':'FEED_NOT_CONFIGURED','reason':'Authorized Reddit API access is not configured.'})
    try:
        age=(now-stamp(out['fetched_at'])).total_seconds()
        if age<0:out['quality']='DATA_INVALID'
        elif age>7200 and out.get('quality')=='DATA_OK':out['quality']='DATA_STALE'
        # Stored state contains no raw text/authors. Expire links/aggregates at24h.
        if age>86400:out={k:out[k] for k in ('provider','quality','fetched_at','reason') if k in out}
    except (ValueError,KeyError,TypeError):
        if out.get('quality')=='DATA_OK':out['quality']='DATA_INCOMPLETE'
    if out.get('quality')!='DATA_OK':out.update(bias='UNAVAILABLE',support=shares([]),threads=[],topics=[])
    return out

def text_for(raw,now=None):
    now=now or datetime.now(timezone.utc);r=fresh_summary(raw,now)
    lines=['WALLSTREETBETS | '+now.astimezone(ET).strftime('%Y-%m-%d %H:%M ET'),'SENTIMENT: '+r.get('bias','UNAVAILABLE')+' | '+r['quality']]
    if r['quality']!='DATA_OK':
        lines += [r.get('reason','No current authorized sample.')]
        if r['quality']=='FEED_NOT_CONFIGURED':lines.append('SETUP: owner needs Reddit-approved Data API access and read-only OAuth credentials in the encrypted local setup form. A Reddit website login alone does not enable the API.')
        return '\n'.join(lines+['Missing Reddit data is not neutral sentiment. /outlook combines price and news evidence.'])
    lines+=[ratio_line('Sampled language',r['support']),r['sample_definition'],
            'Examined: %d posts / %d comments; relevant: %d posts / %d comments.'%(r['posts_examined'],r['comments_examined'],r['relevant_posts'],r['relevant_comments']),
            'Topics: '+(', '.join(r['topics']) or 'No relevant topics')+'.','Fetched: '+stamp(r['fetched_at']).astimezone(ET).strftime('%Y-%m-%d %H:%M ET')]
    for t in r['threads']:lines.append('Thread: '+t['direction']+' | score '+str(t['score'])+' | '+t['url'])
    return '\n'.join(lines+['Selected posts/comments are not representative of investors. Sarcasm, manipulation and option slang can mislead language rules. No forecast probability or buy/sell recommendation.'])

def save(c):
    """Owner-entered approved config only; encrypt and verify before exclusive creation."""
    from monitoring.vault import transform
    validate(c)
    if PRIVATE.exists():raise RuntimeError('EXISTING_CONFIG_PRESERVED')
    raw=json.dumps(c).encode();encrypted=transform(raw)
    if transform(encrypted,True)!=raw:raise RuntimeError('ENCRYPTION_CHECK_FAILED')
    PRIVATE.parent.mkdir(parents=True,exist_ok=True)
    with PRIVATE.open('xb') as f:f.write(encrypted)

def configure():
    """Optional owner-run hidden terminal entry; no secret arguments or stdout load."""
    import sys,getpass
    if not sys.stdin.isatty() or PRIVATE.exists():raise RuntimeError('INTERACTIVE_SETUP_REQUIRED_OR_EXISTING_CONFIG_PRESERVED')
    if input('Do you already have Reddit-approved Data API read access? Type YES: ').strip()!='YES':raise RuntimeError('APPROVED_READ_ACCESS_REQUIRED')
    c={k:getpass.getpass(k+' (hidden): ').strip() for k in ('client_id','client_secret','refresh_token')}
    c.update(user_agent=input('User-Agent windows:AEGIS:1.0 (by /u/YOUR_USERNAME): ').strip(),access_approved=True);validate(c)
    save(c)
    print('ENCRYPTED_REDDIT_READ_CONFIG_SAVED. Restart AEGIS to verify access.')

if __name__=='__main__':
    import sys
    try:
        if sys.argv[1:]!=['configure']:raise RuntimeError('USE_CONFIGURE_NO_SECRET_ARGUMENTS')
        configure()
    except Exception:print('Reddit configuration unavailable or existing configuration preserved. No secrets logged.',file=sys.stderr);raise SystemExit(1)
