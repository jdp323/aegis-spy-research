"""Synthetic-only provider for demonstrations. No production entitlement."""
from data.models import Datum,Quality
class ReplayProvider:
    name='replay-simulated'
    def __init__(self,bars,quote,contracts,now):self.bars=bars;self.quote=quote;self.contracts=contracts;self.now=now
    def datum(self,symbol,kind,payload):return Datum(self.name,symbol,kind,self.now.isoformat(),self.now.isoformat(),Quality.OK,'SIMULATED',{'feed_quality':'SIMULATED',**payload})
    def get_underlying_quote(self,symbol='SPY'):return self.datum(symbol,'quote',self.quote)
    def get_bars(self,symbol='SPY',timeframe='1Min'):return self.datum(symbol,'bars',{'bars':self.bars})
    def get_option_chain(self,symbol='SPY'):return self.datum(symbol,'chain',{'contracts':self.contracts})
    def get_option_quote(self,symbol):return self.datum(symbol,'quote',self.contracts[symbol]['quote']['payload'])
    def get_market_status(self):return {'state':'SIMULATED','active':False}
    def health(self):return {'status':'SIMULATED','provider':self.name,'live_ready':False}
