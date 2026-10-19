import io,json,tempfile,unittest,urllib.error
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from news.market_outlook import RSSProvider,SOURCES,analyze_news,language,shares,lean,build,text_for
from news.reddit import RedditProvider,fresh_summary,NoRedirect

NOW=datetime(2026,10,8,13,15,tzinfo=timezone.utc)
CONFIG={'client_id':'syntheticid','client_secret':'syntheticsecret','refresh_token':'syntheticrefresh',
        'user_agent':'windows:AEGIS:1.0 (by /u/fixture_user)','access_approved':True}
def bundle(titles,provider='cnbc',now=NOW):
    return {'quality':'DATA_OK','fetched_at':now.isoformat(),'articles':[
        {'headline':t,'url':'https://example.test/'+provider+'/'+str(i),'created_at':(NOW-timedelta(hours=1)).isoformat()} for i,t in enumerate(titles)]}
def listing(rows,kind='t3'):return {'kind':'Listing','data':{'children':[{'kind':kind,'data':r} for r in rows]}}
def post(id='abc',title='SPY stocks rally',**changes):
    return {'id':id,'title':title,'selftext':'','subreddit':'wallstreetbets','author':'fixture','created_utc':NOW.timestamp()-3600,'score':100,'num_comments':20,**changes}
def comment(id='def',body='SPY stocks rise',**changes):return post(id=id,body=body,link_id='t3_abc',**changes)

class NewsTests(unittest.TestCase):
    def test_explicit_reaction_negation_conditional_mixed_and_unrelated(self):
        for title,result in [('Stocks rally on earnings','UP'),('SPY shares fall','DOWN'),('Stocks rise but futures fall','NEUTRAL'),
             ('Stocks might rise tomorrow','NEUTRAL'),('Stocks do not rally','NEUTRAL'),('CPI inflation increased by 0.4 percent','NEUTRAL'),
             ('Stocks rallied?','NEUTRAL'),('The garden grows flowers','IRRELEVANT')]:self.assertEqual(language(title)['direction'],result,title)
    def test_evidence_shares_are_not_probabilities_or_forced_fifty_fifty(self):
        s=shares(['UP','DOWN','NEUTRAL','IRRELEVANT']);self.assertEqual(s['total'],3);self.assertEqual(s['percentages']['UP'],33.3)
        self.assertIsNone(shares([])['percentages']);self.assertEqual(lean(shares(['UP','NEUTRAL','NEUTRAL'])),'MIXED')
        self.assertEqual(lean(shares(['UP','UP','DOWN'])),'UP')
    def test_macro_explanation_does_not_guess_surprise_or_direction(self):
        r=language('Inflation CPI increases');self.assertEqual(r['direction'],'NEUTRAL');self.assertIn('expectations',r['reason'])
        self.assertIn('valuations',language('Federal Reserve rate decision')['reason'])
    def test_rss_rfc_dates_exact_source_and_short_records(self):
        body=b'<rss><channel><item><title>Stocks rally</title><link>https://example.test/story?tracking=1</link><pubDate>Thu, 08 Oct 2026 08:30:00 -0400</pubDate></item></channel></rss>'
        r=RSSProvider(lambda url:body).collect('cnbc',NOW)
        self.assertEqual(r['quality'],'DATA_OK');self.assertEqual(r['articles'][0]['url'],'https://example.test/story')
        self.assertFalse(r['coverage_complete']);self.assertFalse(r['actionable']);self.assertEqual(r['source_url'],SOURCES['cnbc'])
    def test_atom_feed_and_html_are_data_not_instructions(self):
        body=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>&lt;b&gt;SPY rises&lt;/b&gt;</title><link href="https://example.test/story"/><updated>2026-10-08T12:30:00Z</updated></entry></feed>'
        r=RSSProvider(lambda u:body).collect('fed_policy',NOW);self.assertEqual(r['articles'][0]['headline'],'SPY rises')
    def test_malicious_xml_oversize_and_future_titles_fail_closed(self):
        for body in (b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///secret">]><rss/>',b'x'*(1024*1024+1),b'<html>blocked</html>',
                     b'<rss><item><title>SPY rises</title><link>https://secret:password@example.test</link><pubDate>Thu, 08 Oct 2026 08:30:00 -0400</pubDate></item></rss>',
                     b'<rss><item><title>SPY rises</title><link>https://example.test</link><pubDate>Thu, 08 Oct 2026 10:30:00 -0400</pubDate></item></rss>'):
            r=RSSProvider(lambda u:body).collect('bls',NOW);self.assertEqual(r['quality'],'DATA_INCOMPLETE');self.assertEqual(r['articles'],[]);self.assertNotIn('password',str(r))
    def test_failed_provider_is_explicit_and_others_remain_usable(self):
        def fail(u):raise urllib.error.HTTPError(u,403,'fixture-secret',{},None)
        r=RSSProvider(fail).collect('bea',NOW);self.assertEqual(r['reason'],'HTTP_403');self.assertNotIn('fixture-secret',str(r))
        n=analyze_news({'bea':r,'cnbc':bundle(['Stocks rally','Futures rise'])},NOW);self.assertEqual(n['bias'],'UP');self.assertEqual(n['source_health']['bea']['quality'],'DATA_INCOMPLETE')
    def test_dedupe_stale_future_irrelevant_and_old_articles(self):
        a=bundle(['Stocks rally','SPY rises','Flowers bloom']);b=bundle(['Stocks rally'],'alpaca')
        b['articles'][0]['url']=a['articles'][0]['url'];a['articles'].append({'headline':'Stocks fall','url':'https://example.test/old','created_at':(NOW-timedelta(days=3)).isoformat()})
        n=analyze_news({'cnbc':a,'alpaca':b,'stale':bundle(['Stocks fall'],now=NOW-timedelta(hours=1))},NOW)
        self.assertEqual(n['support']['total'],2);self.assertEqual(n['bias'],'UP');self.assertEqual(n['source_health']['stale']['quality'],'DATA_STALE')
        self.assertEqual(analyze_news({'future':bundle(['Stocks fall'],now=NOW+timedelta(seconds=1))},NOW)['support']['total'],0)
    def test_fresh_query_cannot_make_old_or_future_publication_current_evidence(self):
        # Query receipt and publication timestamps are independent evidence.
        # A fresh official/provider fetch cannot revive yesterday's expired vote
        # or admit a source time ahead of the actual analysis clock.
        for published in (NOW-timedelta(hours=48,microseconds=1),NOW+timedelta(microseconds=1)):
            with self.subTest(publication=published.isoformat()):
                raw=bundle(['Stocks rally','Futures rise'])
                for article in raw['articles']:article['created_at']=published.isoformat()
                result=analyze_news({'cnbc':raw},NOW)
                self.assertEqual(result['source_health']['cnbc']['quality'],'DATA_OK')
                self.assertEqual(result['support']['total'],0)
                self.assertEqual(result['bias'],'UNAVAILABLE');self.assertEqual(result['items'],[])
                self.assertFalse(result['validated_prediction']);self.assertFalse(result['coverage_complete'])
    def test_publication_recency_compares_instants_across_source_timezones(self):
        raw=bundle(['Stocks rally','Futures fall'])
        # 08:30 EDT is 12:30 UTC and is newer than 12:00 UTC,
        # even though its ISO string starts with an earlier wall-clock hour.
        raw['articles'][0]['created_at']='2026-10-08T08:30:00-04:00'
        raw['articles'][1]['created_at']='2026-10-08T12:00:00+00:00'
        result=analyze_news({'cnbc':raw},NOW)
        self.assertEqual([x['headline'] for x in result['items']],['Stocks rally','Futures fall'])
        self.assertEqual(result['support']['counts'],{'UP':1,'DOWN':1,'NEUTRAL':0})

class RedditTests(unittest.TestCase):
    def provider(self,transport):return RedditProvider(transport,lambda:dict(CONFIG))
    def transport(self,path,params):
        if path.endswith('/top'):return listing([post()])
        return [listing([post()]),listing([comment()],kind='t1')]
    def test_missing_approval_never_accesses_public_api(self):
        calls=[];p=RedditProvider(lambda *a:calls.append(a),lambda:None);r=p.collect(NOW)
        self.assertEqual(r['quality'],'FEED_NOT_CONFIGURED');self.assertEqual(calls,[]);self.assertEqual(r['support']['total'],0)
        p=RedditProvider(lambda *a:calls.append(a),lambda:{**CONFIG,'access_approved':False});self.assertEqual(p.collect(NOW)['quality'],'DATA_INCOMPLETE');self.assertEqual(calls,[])
    def test_top_posts_and_comments_are_sampled_without_raw_text_or_authors(self):
        r=self.provider(self.transport).collect(NOW);self.assertEqual(r['quality'],'DATA_OK');self.assertEqual(r['bias'],'UP');self.assertEqual(r['support']['total'],2)
        self.assertEqual(r['comments_examined'],1);self.assertNotIn('SPY stocks rally',str(r));self.assertNotIn('author',str(r));self.assertFalse(r['raw_content_stored']);self.assertFalse(r['representative_sample'])
    def test_irrelevant_comments_and_deleted_posts_do_not_vote(self):
        def transport(path,params):
            if path.endswith('/top'):return listing([post(),post('xyz','SPY falls',author='[deleted]')])
            return [listing([post()]),listing([comment(body='Bananas are tasty'),comment('ghi','[deleted]')],kind='t1')]
        r=self.provider(transport).collect(NOW);self.assertEqual(r['support']['total'],1);self.assertEqual(r['relevant_comments'],0);self.assertEqual(r['bias'],'MIXED')
    def test_comment_from_wrong_thread_discards_partial_result(self):
        def transport(path,params):
            if path.endswith('/top'):return listing([post()])
            return [listing([post()]),listing([comment(link_id='t3_other')],kind='t1')]
        r=self.provider(transport).collect(NOW);self.assertEqual(r['quality'],'DATA_INCOMPLETE');self.assertEqual(r['support']['total'],0);self.assertEqual(r['threads'],[])
    def test_three_threads_and_twenty_comments_are_request_bounds(self):
        calls=[]
        def transport(path,params):
            calls.append((path,params))
            if path.endswith('/top'):return listing([post(str(i)) for i in range(25)])
            id=path.split('/')[-1];return [listing([post(id)]),listing([],kind='t1')]
        r=self.provider(transport).collect(NOW);self.assertEqual(r['quality'],'DATA_OK');self.assertEqual(len(calls),4);self.assertEqual(len(r['threads']),3)
        self.assertTrue(all(p['limit']==20 and p['depth']==1 for _,p in calls[1:]))
    def test_rate_limit_respected_and_errors_never_leak_token(self):
        calls=[]
        def transport(path,params):calls.append(path);raise urllib.error.HTTPError(path,429,'secret-token',{'Retry-After':'120'},None)
        p=self.provider(transport);r=p.collect(NOW);self.assertEqual(r['reason'],'REDDIT_HTTP_429');self.assertNotIn('secret-token',str(r))
        p.collect(NOW+timedelta(seconds=119));self.assertEqual(len(calls),1);p.collect(NOW+timedelta(seconds=121));self.assertEqual(len(calls),2)
    def test_timestamps_wrong_subreddit_and_oversize_listing_rejected(self):
        for rows in ([post(subreddit='other')],[post(created_utc=NOW.timestamp()+1)],[post(created_utc=NOW.timestamp()-3*86400)],[post(score=True)],[post()]*26):
            r=self.provider(lambda p,q:listing(rows)).collect(NOW);self.assertEqual(r['quality'],'DATA_INCOMPLETE');self.assertEqual(r['support']['total'],0)
    def test_option_slang_and_sarcasm_are_not_naive_votes(self):
        for text in ('SPY selling puts','SPY earnings call','SPY rally /s','SPY might fall'):
            self.assertEqual(language(text,social=True)['direction'],'NEUTRAL',text)
        self.assertEqual(language('SPY buying calls',social=True)['direction'],'UP')
        self.assertEqual(language('SPY buying puts',social=True)['direction'],'DOWN')
    def test_stale_future_expired_summary_cannot_show_sentiment(self):
        raw=self.provider(self.transport).collect(NOW)
        self.assertEqual(fresh_summary(raw,NOW+timedelta(seconds=7201))['bias'],'UNAVAILABLE')
        self.assertEqual(fresh_summary(raw,NOW-timedelta(seconds=1))['quality'],'DATA_INVALID')
        self.assertEqual(fresh_summary(raw,NOW+timedelta(days=2))['threads'],[])
    def test_redirect_rejected_before_authorization_can_be_forwarded(self):
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,302,'',{},'https://attacker.test')
    def test_oauth_refresh_is_cached_in_memory_and_only_read_paths_are_called(self):
        p=RedditProvider(config_loader=lambda:dict(CONFIG));calls=[]
        def fetch(req):
            calls.append(req)
            if req.full_url.endswith('/access_token'):return {'token_type':'bearer','access_token':'synthetic-access','expires_in':3600,'scope':'read'}
            return listing([])
        p.fetch=fetch;r=p.collect(NOW);self.assertEqual(r['quality'],'DATA_OK')
        p.collect(NOW+timedelta(seconds=1));self.assertEqual(sum('/access_token' in q.full_url for q in calls),1)
        self.assertTrue(all('/access_token' in q.full_url or q.full_url.startswith('https://oauth.reddit.com/r/wallstreetbets/top') for q in calls))
        self.assertNotIn('synthetic-access',str(r));self.assertNotIn('syntheticrefresh',str(r))
    def test_oauth_without_read_scope_never_queries_posts(self):
        p=RedditProvider(config_loader=lambda:dict(CONFIG));calls=[]
        def fetch(req):calls.append(req);return {'token_type':'bearer','access_token':'synthetic-access','expires_in':3600,'scope':'identity'}
        p.fetch=fetch;self.assertEqual(p.collect(NOW)['quality'],'DATA_INCOMPLETE');self.assertEqual(len(calls),1)
    def test_inaccessible_comments_discard_the_entire_sentiment(self):
        def transport(path,params):
            if path.endswith('/top'):return listing([post()])
            raise urllib.error.HTTPError(path,403,'not entitled',{},None)
        r=self.provider(transport).collect(NOW);self.assertEqual(r['reason'],'REDDIT_HTTP_403');self.assertEqual(r['support']['total'],0)

class IntegratedOutlookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'test.sqlite');self.addCleanup(self.store.close)
    def test_reddit_does_not_override_conflicting_price_and_news(self):
        self.store.put('market_news:cnbc',bundle(['Stocks fall','Futures drop']))
        self.store.put('reddit_sentiment',{'quality':'DATA_OK','fetched_at':NOW.isoformat(),'bias':'UP','support':shares(['UP']*50)})
        with patch('news.market_outlook.market_evidence',return_value={'bias':'UP','mode':'FIXTURE ONLY'}):r=build(self.store,NOW)
        self.assertEqual(r['bias'],'MIXED');self.assertFalse(r['validated_prediction']);self.assertFalse(r['option_recommendation'])
    def test_news_only_bias_labels_missing_price_and_no_calibrated_prediction(self):
        self.store.put('market_news:cnbc',bundle(['Stocks fall','Futures drop']))
        with patch('news.market_outlook.market_evidence',return_value={'bias':'UNAVAILABLE','mode':'NO CURRENT PRICE'}):r=build(self.store,NOW)
        self.assertEqual(r['bias'],'DOWN');self.assertIn('current price trend missing',text_for(r));self.assertIn('not odds',text_for(r));self.assertLess(len(text_for(r,'news')),3500)
    def test_shared_outlook_does_not_read_position_or_account_fields(self):
        self.store.put('positions:owner',{'balance':'PRIVATE_SECRET'});self.store.put('market_news:cnbc',bundle(['Stocks rise','Futures rally']))
        with patch('news.market_outlook.market_evidence',return_value={'bias':'UP','mode':'FIXTURE ONLY'}):r=build(self.store,NOW)
        self.assertNotIn('PRIVATE_SECRET',text_for(r));self.assertEqual(r['bias'],'UP')
    def test_morning_report_contains_news_and_social_with_one_delivery_id(self):
        from monitoring.premarket_brief import update
        self.store.put('market_news:cnbc',bundle(['Stocks rise','Futures rally']));events=[]
        with patch('news.market_outlook.market_evidence',return_value={'bias':'UP','mode':'FIXTURE ONLY'}):
            update(self.store,{}, {},lambda s,id,t,**kw:events.append((id,t,kw)),NOW,lambda *a:{})
            update(self.store,{}, {},lambda *a,**kw:self.fail('Duplicate morning alert'),NOW+timedelta(seconds=1),lambda *a:{})
        self.assertEqual(len(events),1);self.assertIn('MORNING BRIEF',events[0][1]);self.assertIn('News language',events[0][1]);self.assertIn('WSB:',events[0][1]);self.assertEqual(events[0][2]['kind'],'RESEARCH')
    def test_command_recomputes_outlook_and_retains_private_tenant_validation(self):
        from core.bot_commands import execute
        with patch('core.bot_commands.Store',return_value=self.store),patch('news.market_outlook.market_evidence',return_value={'bias':'UNAVAILABLE','mode':'FIXTURE ONLY'}):
            self.assertIn('SPY OUTLOOK',execute({'command':'outlook','tenant':'a'*24}))
        # execute closes its Store; reopen only the synthetic database.
        self.store=Store(Path(self.temp.name)/'test.sqlite');self.addCleanup(self.store.close)
        with self.assertRaises(ValueError):execute({'command':'outlook','tenant':'../owner'})
    def test_new_major_news_can_notify_even_when_price_data_is_missing(self):
        from monitoring.research_alerts import update
        from core.sessions import market_session
        at=NOW.replace(hour=14);self.store.put('market_news:cnbc',bundle(['Stocks rally','Futures rise'],now=at));events=[]
        def publish(s,id,text,**kw):events.append(text)
        with patch('news.market_outlook.market_evidence',return_value={'bias':'UNAVAILABLE','mode':'NO CURRENT PRICE'}):
            update(self.store,{},market_session(at),{},publish,at)
            self.assertIsNone(update(self.store,{},market_session(at),{},publish,at+timedelta(seconds=1)))
            later=at+timedelta(minutes=10);self.store.put('market_news:cnbc',bundle(['Stocks fall','Futures drop'],now=later))
            update(self.store,{},market_session(later),{},publish,later)
        self.assertEqual(len(events),2);self.assertIn('BIAS: DOWN',events[-1]);self.assertIn('current price trend missing',events[-1])
    def test_refetching_identical_news_does_not_count_as_a_new_driver(self):
        from monitoring.research_alerts import update
        from core.sessions import market_session
        at=NOW.replace(hour=14);self.store.put('market_news:cnbc',bundle(['Stocks rally','Futures rise'],now=at));events=[]
        with patch('news.market_outlook.market_evidence',return_value={'bias':'UNAVAILABLE','mode':'NO CURRENT PRICE'}):
            update(self.store,{},market_session(at),{},lambda *a,**kw:events.append(a),at)
            later=at+timedelta(minutes=10);self.store.put('market_news:cnbc',bundle(['Stocks rally','Futures rise'],now=later))
            self.assertIsNone(update(self.store,{},market_session(later),{},lambda *a,**kw:events.append(a),later))
        self.assertEqual(len(events),1)

if __name__=='__main__':unittest.main()
