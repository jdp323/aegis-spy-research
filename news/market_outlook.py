"""Small, source-attributed market outlooks. Evidence shares are not probabilities.

Published releases are not an upcoming-event calendar. External text is data only;
it cannot change configuration, place orders or become an executable instruction.
"""
import hashlib,json,re,urllib.request,urllib.error,xml.etree.ElementTree as XML
from email.utils import parsedate_to_datetime
from datetime import datetime,timezone,timedelta
from html import unescape
from core.sessions import ET,market_session
from data.models import stamp
from data.research_inputs import safe_url

VERSION='spy-market-outlook-v2'
SOURCES={
    'fed_policy':'https://www.federalreserve.gov/feeds/press_monetary.xml',
    'fed_speeches':'https://www.federalreserve.gov/feeds/speeches.xml',
    'bls':'https://www.bls.gov/feed/bls_latest.rss',
    'bea':'https://apps.bea.gov/rss/rss.xml',
    'cnbc':'https://www.cnbc.com/id/100003114/device/rss/rss.html',
}
USER_AGENT='AEGIS/1.0 (local read-only market research RSS reader)'
MAX_BODY=1024*1024
RELEVANT=re.compile(r'\b(spy|s&p|s\s*&\s*p|stock markets?|stocks?|equities|equity|wall street|futures|inflation|cpi|pce|payrolls?|unemployment|jobs report|employment situation|gdp|federal reserve|fed|fomc|treasur\w*|yields?|interest rates?|tariffs?|recession|geopolit\w*|war|ceasefire|oil)\b',re.I)
MAJOR=re.compile(r'\b(spy|s&p|s\s*&\s*p|stock markets?|wall street|stock futures|futures|inflation|cpi|pce|payrolls?|unemployment|jobs report|employment situation|gdp|federal reserve|fed|fomc|treasur\w*|bond yields?|interest rates?|recession|geopolit\w*|war|ceasefire)\b',re.I)
TOPICS={
    'Rates / Fed':r'\b(fed|fomc|federal reserve|rates?|yields?|treasur\w*)\b',
    'Inflation':r'\b(inflation|cpi|pce|consumer price|producer price)\b',
    'Jobs / growth':r'\b(jobs?|payrolls?|employment|unemployment|gdp|recession|growth)\b',
    'Geopolitics / trade':r'\b(war|ceasefire|tariffs?|geopolit\w*|oil|sanctions?)\b',
    'Market reaction':r'\b(spy|s&p|stocks?|equities|equity|wall street|futures|market)\b',
}
# Require an explicit market subject/reaction; macro surprises cannot be inferred
# from a number without expectations. These are transparent language rules.
SUBJECT=r'\b(stocks?|equities|futures|s&p(?:\s*500)?|spy|wall street|stock market)\b'
# Only connect an explicit market subject to its own reaction. Arbitrary text
# between subject and verb wrongly voted "stock market's cushion against higher
# rates" UP, and could assign a Treasury-yield move to stock prices.
LINK=r'(?:\s+(?:shares|index|prices|are|were|is|was|open|opened|trade|trades|trading|end|ended|close|closed|finish|finished|move|moved|edge|edged|post|posts|record|records|sharply|slightly|broadly|modestly|further|significantly|steadily|today|again|all)){0,5}\s+'
UP=re.compile(SUBJECT+LINK+r'\b(rall(?:y|ies|ied)|rise|rises|rising|rose|gain|gains|gained|climb|climbs|climbed|surge|surges|surged|higher|rebound|rebounds|advance|advances)\b',re.I)
DOWN=re.compile(SUBJECT+LINK+r'\b(fall|falls|falling|fell|drop|drops|dropped|slip|slips|slipped|sink|sinks|sank|lower|selloff|sell-off|tumble|tumbles|tumbled|decline|declines|declined)\b',re.I)
UNCERTAIN=re.compile(r'\b(not|never|may|might|could|would|if|forecast|predict\w*|expect\w*|potential|should|no longer)\b|\?',re.I)

def clean(value,limit=200):
    if not isinstance(value,str):return ''
    value=unescape(re.sub(r'<[^>]{0,2000}>',' ',value))
    return re.sub(r'\s+',' ',re.sub(r'[\x00-\x1f\x7f]',' ',value)).strip()[:limit]

def language(text,social=False):
    """Unambiguous text direction only; mixed, conditional and negated stay neutral."""
    text=clean(text,1000)
    if not RELEVANT.search(text):return {'direction':'IRRELEVANT','reason':'No broad-market or macro topic.'}
    if UNCERTAIN.search(text) or '/s' in text.lower():return {'direction':'NEUTRAL','reason':'Conditional, uncertain, negated or sarcastic wording.'}
    up=bool(UP.search(text));down=bool(DOWN.search(text))
    if social:
        # Selling options is not the same directional exposure as buying them.
        if not re.search(r'\b(sell|selling|sold|short|shorting)\b',text,re.I):
            up |= bool(re.search(r'\b(buy|buying|bought|long)\b.{0,18}\bcalls\b|\bbullish\b',text,re.I))
            down |= bool(re.search(r'\b(buy|buying|bought|long)\b.{0,18}\bputs\b|\bbearish\b',text,re.I))
    direction='UP' if up and not down else 'DOWN' if down and not up else 'NEUTRAL'
    reason='Explicit upward market language.' if direction=='UP' else 'Explicit downward market language.' if direction=='DOWN' else 'No unambiguous direction; macro effect depends on expectations and market reaction.'
    if direction=='NEUTRAL' and not social:
        if re.search(TOPICS['Inflation'],text,re.I):reason='Inflation affects the rate outlook. The surprise versus expectations and price response need confirmation.'
        elif re.search(TOPICS['Rates / Fed'],text,re.I):
            if re.search(r'\b(hikes?|hawkish|higher rates?|rising yields?)\b',text,re.I):reason='Higher-rate or hawkish language suggests valuation pressure on stocks; whether that is priced in needs confirmation.'
            elif re.search(r'\b(cuts?|dovish|lower rates?|falling yields?)\b',text,re.I):reason='Lower-rate or dovish language can support valuations, but recession-driven cuts can still hurt stocks.'
            else:reason='Rates and bond yields affect stock valuations; policy direction and the actual price reaction need confirmation.'
        elif re.search(TOPICS['Jobs / growth'],text,re.I):reason='Strong growth can support earnings but delay rate cuts; weak growth can raise recession risk. Context matters.'
        elif re.search(TOPICS['Geopolitics / trade'],text,re.I):reason='Trade or geopolitical shocks can affect risk appetite, oil and inflation; the net stock-market direction is uncertain.'
    return {'direction':direction,'reason':reason}

def shares(votes):
    counts={k:votes.count(k) for k in ('UP','DOWN','NEUTRAL')};total=sum(counts.values())
    return {'counts':counts,'total':total,'percentages':{k:round(v/total*100,1) for k,v in counts.items()} if total else None,
            'meaning':'TEXT_OR_INDICATOR_EVIDENCE_SHARES_NOT_FORECAST_PROBABILITIES'}

def lean(s):
    c=s['counts'];directional=c['UP']+c['DOWN']
    if not s['total']:return 'UNAVAILABLE'
    if directional<2 or directional/s['total']<.5:return 'MIXED'
    return 'UP' if c['UP']>c['DOWN'] else 'DOWN' if c['DOWN']>c['UP'] else 'MIXED'

class RSSProvider:
    def __init__(self,transport=None):self.transport=transport or self.fetch
    @staticmethod
    def fetch(url):
        req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml, application/atom+xml, text/xml'})
        with urllib.request.urlopen(req,timeout=6) as response:
            if response.geturl().split('/',3)[2].lower()!=url.split('/',3)[2].lower():raise ValueError('FEED_REDIRECT_HOST_CHANGED')
            body=response.read(MAX_BODY+1)
        if len(body)>MAX_BODY:raise ValueError('FEED_TOO_LARGE')
        return body
    def collect(self,key,now=None):
        now=now or datetime.now(timezone.utc);url=SOURCES[key]
        out={'provider':key,'source_url':url,'fetched_at':now.isoformat(),'quality':'DATA_INCOMPLETE','articles':[],
             'coverage_complete':False,'delay_status':'UNVERIFIED','data_type':'published_headlines','actionable':False}
        try:
            body=self.transport(url)
            if not isinstance(body,bytes) or len(body)>MAX_BODY or re.search(br'<!\s*(DOCTYPE|ENTITY)',body,re.I):raise ValueError('UNSAFE_FEED_XML')
            doc=XML.fromstring(body);nodes=doc.findall('.//item') or doc.findall('.//{http://www.w3.org/2005/Atom}entry')
            if len(nodes)>500:raise ValueError('FEED_ITEM_LIMIT')
            rows=[];rejected=0
            for node in nodes[:100]:
                def value(name):
                    el=node.find(name)
                    if el is None:el=node.find('{http://www.w3.org/2005/Atom}'+name)
                    return ''.join(el.itertext()).strip() if el is not None else ''
                try:
                    title=clean(value('title'),160)
                    if not title:raise ValueError('EMPTY_TITLE')
                    published=value('pubDate') or value('published') or value('updated')
                    try:t=stamp(published)
                    except ValueError:t=parsedate_to_datetime(published)
                    if t.tzinfo is None or t>now:raise ValueError('INVALID_PUBLICATION_TIME')
                    if now-t>timedelta(days=7):continue
                    link=value('link')
                    if not link:
                        links=node.findall('{http://www.w3.org/2005/Atom}link')
                        link=next((e.get('href','') for e in links if e.get('rel','alternate')=='alternate'),'')
                    rows.append({'headline':title,'url':safe_url(link),'created_at':t.isoformat(),'provider':key})
                except (ValueError,TypeError,KeyError,OverflowError):rejected+=1
            out.update(quality='DATA_OK' if nodes and rejected<len(nodes[:100]) else 'DATA_INCOMPLETE',articles=rows[:40],
                       rejected_items=rejected,sha256=hashlib.sha256(body).hexdigest(),reason='PUBLISHED_FEED_ONLY')
        except urllib.error.HTTPError as error:out['reason']='HTTP_'+str(error.code)
        except Exception:out['reason']='FEED_UNAVAILABLE_OR_INVALID'
        return out

def fresh(value,now,max_age=1800):
    out=dict(value or {'quality':'DATA_INCOMPLETE','articles':[],'reason':'NOT_FETCHED'})
    try:
        age=(now-stamp(out['fetched_at'])).total_seconds();out['query_age_seconds']=age
        if age<0:out['quality']='DATA_INVALID'
        elif age>max_age and out.get('quality')=='DATA_OK':out['quality']='DATA_STALE'
    except (ValueError,KeyError,TypeError):out['quality']='DATA_INCOMPLETE'
    return out

def analyze_news(bundles,now=None):
    now=now or datetime.now(timezone.utc);items=[];seen_urls=set();seen_titles=set();health={};votes=[]
    for key,raw in bundles.items():
        source=fresh(raw,now);health[key]={k:source.get(k) for k in ('quality','fetched_at','reason','query_age_seconds')}
        if source['quality']!='DATA_OK':continue
        for r in source.get('articles',[])[:40]:
            try:
                t=stamp(r['created_at']);headline=clean(r['headline'],160);url=safe_url(r['url']);canonical=re.sub(r'[^a-z0-9]','',headline.lower())
                if not 0<=(now-t).total_seconds()<=48*3600 or not headline or url in seen_urls or canonical in seen_titles:continue
                seen_urls.add(url);seen_titles.add(canonical);e=language(headline)
                if e['direction']=='IRRELEVANT':continue
                # Individual retailer guidance, tanker stories and stock-pick
                # lists do not establish the broad-market direction.
                if key not in ('fed_policy','fed_speeches','bls','bea') and not MAJOR.search(headline) and e['direction']=='NEUTRAL':continue
                votes.append(e['direction']);topics=[k for k,p in TOPICS.items() if re.search(p,headline,re.I)]
                items.append({'headline':headline,'url':url,'published_at':t.isoformat(),'provider':key,'direction':e['direction'],'reason':e['reason'],'topics':topics})
            except (KeyError,ValueError,TypeError,OverflowError):continue
    # Major monetary/macro drivers lead; recency breaks ties. Do not crowd the
    # brief with unrelated corporate stories just because they are newest.
    def priority(r):
        # Provider strings can use different UTC offsets. Compare actual aware
        # instants, never lexicographic local-clock representations.
        return (3 if r['provider'] in ('fed_policy','bls','bea') else 2 if any(t in r['topics'] for t in ('Rates / Fed','Inflation','Jobs / growth')) else 1,stamp(r['published_at']))
    items.sort(key=priority,reverse=True);s=shares(votes)
    return {'version':VERSION,'analyzed_at':now.isoformat(),'bias':lean(s),'support':s,'items':items[:30],'source_health':health,
            'topics':sorted({t for r in items for t in r['topics']}),'coverage_complete':False,'validated_prediction':False,
            'note':'Headline language only; reports can describe moves already priced in. No surprise, consensus forecast or complete calendar inferred.'}

def market_evidence(store,now,premarket=None):
    from research.live_trend import evaluate
    live=evaluate(store,now)
    if live['status']=='LIVE_TREND':return {'bias':live['direction'],'mode':live['feed'].upper()+' LIVE QUOTE / COMPLETED MINUTE BARS','as_of':live['quote_time'],'counts':live['counts'],'price':live['mid']}
    if premarket and premarket.get('quality') in ('PUBLIC_RESEARCH_ONLY','IEX_RESEARCH_ONLY'):
        # Current-date reports are still historical observations, not live quotes.
        try:
            end=stamp(premarket['as_of_bar'])+timedelta(minutes=5)
            if 0<=(now-end).total_seconds()<=900 and premarket['date']==now.astimezone(ET).date().isoformat():
                bias={'BULLISH':'UP','BEARISH':'DOWN'}.get(premarket['bias'],'MIXED')
                return {'bias':bias,'mode':'PREMARKET IEX AUTHORIZED HISTORICAL BARS; SINGLE EXCHANGE' if premarket['quality']=='IEX_RESEARCH_ONLY' else 'PREMARKET PUBLIC BARS; DELAY UNVERIFIED','as_of':end.isoformat(),'price':premarket['levels']['last']}
        except (ValueError,KeyError,TypeError):pass
    from research.basic_trend import analyze
    from data.trend_spy import load
    basic=analyze(load(),now)
    if basic['direction']!='UNAVAILABLE':return {'bias':basic['direction'],'mode':'PUBLIC FIVE-MINUTE BARS; DELAY UNVERIFIED','as_of':basic['as_of'],'counts':basic['support']['counts'],'price':basic['price']}
    return {'bias':'UNAVAILABLE','mode':'NO USABLE CURRENT PRICE TREND','reason':live['reason']}

def build(store,now=None,premarket=None,observation=None):
    now=now or datetime.now(timezone.utc)
    bundles={k:store.get('market_news:'+k) for k in SOURCES};bundles['alpaca']=store.get('news_headlines')
    news=analyze_news(bundles,now);market=market_evidence(store,now,premarket)
    if observation and observation.get('quality')=='PUBLIC_RESEARCH_ONLY' and 'LIVE QUOTE' not in market['mode'] and market_session(now)['active']:
        trend=observation['trend'];market={'bias':'UP' if trend=='UPWARD 5m STRUCTURE' else 'DOWN' if trend=='DOWNWARD 5m STRUCTURE' else 'MIXED',
            'mode':'HISTORICAL PUBLIC FIVE-MINUTE BARS; DELAY UNVERIFIED','as_of':(observation['bar']+timedelta(minutes=5)).isoformat(),'price':observation['levels']['last_close']}
    from news.reddit import fresh_summary
    social=fresh_summary(store.get('reddit_sentiment'),now)
    m,n=market['bias'],news['bias']
    # Reddit is context, never the deciding vote. News alone gets a labeled lens.
    bias=m if m in ('UP','DOWN') and n in (m,'MIXED','UNAVAILABLE') else 'MIXED' if m!='UNAVAILABLE' else n
    basis='Price trend + news context' if m!='UNAVAILABLE' else 'News language only; current price trend missing'
    return {'version':VERSION,'generated_at':now.isoformat(),'session':market_session(now)['state'],'bias':bias,'basis':basis,
            'market':market,'news':news,'reddit':social,'action':'RESEARCH_ONLY','validated_prediction':False,'option_recommendation':False}

def ratio_line(label,s):
    if not s or not s.get('total'):return label+': no usable directional sample.'
    c=s['counts'];n=s['total']
    return label+': %d of %d UP / %d of %d DOWN / %d of %d NEUTRAL; correlated checks, not probabilities.'%(c['UP'],n,c['DOWN'],n,c['NEUTRAL'],n)

def text_for(r,detail='outlook'):
    at=stamp(r['generated_at']).astimezone(ET).strftime('%Y-%m-%d %H:%M ET')
    lines=['SPY '+('NEWS' if detail=='news' else 'OUTLOOK')+' | '+at,'BIAS: '+r['bias']+' — '+r['basis']+'.']
    m,n=r['market'],r['news'];lines+=['PRICE TREND: '+m['bias']+' | '+m['mode']+'.']
    if m['bias']=='UNAVAILABLE':
        from core.verdict import next_open
        generated=stamp(r['generated_at']);session=market_session(generated);nxt=next_open(generated)
        if not session['active']:
            lines.append('SESSION: '+session['state']+' — regular-session trend is not running now.')
            if nxt:lines.append('Next regular open: '+nxt.strftime('%a %Y-%m-%d %H:%M ET')+'; morning outlook: '+(nxt-timedelta(minutes=15)).strftime('%H:%M ET')+'.')
            lines.append('Overnight news is context; it cannot confirm the direction of the next session.')
        else:
            lines.append('Price inputs not ready: '+str(m.get('reason','fresh quote and completed current-session history required'))+'.')
    if m.get('as_of'):lines.append('Price evidence through '+stamp(m['as_of']).astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET')+'.')
    if m.get('counts'):lines.append(ratio_line('Price checks',shares([k for k,v in m['counts'].items() for _ in range(v)])))
    lines+=[ratio_line('News language',n['support']),'MAJOR TOPICS: '+(', '.join(n['topics']) or 'No fresh relevant headlines available')+'.']
    # Short excerpts, not full article copies; cap each publisher's quoted words.
    word_budget={};selected=0
    for item in n['items']:
        key=item['provider'];remaining=24-word_budget.get(key,0)
        if remaining<4:continue
        words=item['headline'].split()[:min(8,remaining)];word_budget[key]=word_budget.get(key,0)+len(words)
        lines.append('• '+item['direction']+' | '+' '.join(words)+'… ('+key+', '+stamp(item['published_at']).astimezone(ET).strftime('%m-%d %H:%M ET')+')')
        lines.append('  '+item['reason'])
        if detail=='news':lines.append(item['url'])
        selected+=1
        if selected>=(5 if detail=='news' else 3):break
    social=r['reddit'];lines.append('WSB: '+social.get('bias','UNAVAILABLE')+'.')
    if social['quality']=='DATA_OK':lines.append(ratio_line('Sampled WSB language',social['support'])+' Top daily posts + sampled top comments; not all retail traders.')
    else:lines.append(social.get('reason','Reddit sentiment is not established.'))
    valid=[k for k,h in n['source_health'].items() if h['quality']=='DATA_OK'];missing=[k for k,h in n['source_health'].items() if h['quality']!='DATA_OK']
    lines+=['Sources checked: '+(', '.join(valid) or 'none')+'.'+(' Unavailable/stale: '+', '.join(missing)+'.' if missing else ''),
            'READING: Evidence shares, not odds of a rise/fall. Headline moves may already be priced in; complete upcoming-event coverage is not established.',
            'NEWS DELIVERY: Delay UNVERIFIED; publication time is shown separately from analysis time.',
            'WATCH: Opening price/volume can confirm or reverse the morning bias. Reddit is noisy context and does not change the price/news bias.',
            'Research outlook; no option trade instruction.',
            '/trend = current price analysis | /news = drivers | /sentiment = WSB']
    return '\n'.join(lines)[:3400]
