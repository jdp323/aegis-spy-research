"""Adversarial adapter input tests; synthetic fixtures never establish entitlements."""
import copy,unittest
from datetime import datetime,timezone,timedelta
from data.massive_research import MassiveResearchProvider
NOW=datetime(2026,10,6,14,tzinfo=timezone.utc)
class MassiveBarSchemaTests(unittest.TestCase):
    def doc(self):
        return {'ticker':'SPY','status':'OK','adjusted':False,'results':[{'t':int((NOW-timedelta(minutes=5)).timestamp()*1000),'o':600,'h':602,'l':599,'c':601,'v':1000}]}
    def result(self,doc):return MassiveResearchProvider(lambda path,params:doc,lambda:NOW).get_bars()
    def rejected(self,doc):
        d=self.result(doc);self.assertEqual(d.payload,{});self.assertNotEqual(d.quality,'DATA_OK');self.assertNotEqual(d.entitlement,'REALTIME')
    def test_nonfinite_boolean_and_missing_prices_rejected(self):
        for value in (float('nan'),float('inf'),True,None,'601'):
            with self.subTest(value=value):
                doc=self.doc();doc['results'][0]['c']=value;self.rejected(doc)
    def test_negative_boolean_or_missing_volume_rejected(self):
        for value in (-1,False,None,float('inf')):
            with self.subTest(value=value):
                doc=self.doc();doc['results'][0]['v']=value;self.rejected(doc)
    def test_inconsistent_ohlc_rejected(self):
        for patch in ({'l':0},{'l':603},{'c':603},{'o':598}):
            doc=self.doc();doc['results'][0].update(patch);self.rejected(doc)
    def test_timestamp_units_alignment_type_and_future_rejected(self):
        good=self.doc()['results'][0]['t']
        for value in (True,str(good),good/1.,good//1000,good+1,int((NOW+timedelta(minutes=5)).timestamp()*1000)):
            with self.subTest(value=value):
                doc=self.doc();doc['results'][0]['t']=value;self.rejected(doc)
    def test_duplicates_unordered_and_nonobject_results_rejected(self):
        doc=self.doc();doc['results'].append(copy.deepcopy(doc['results'][0]));self.rejected(doc)
        doc=self.doc();row=copy.deepcopy(doc['results'][0]);row['t']-=300000;doc['results'].append(row);self.rejected(doc)
        for rows in ([None],{},'malformed'):
            doc=self.doc();doc['results']=rows;self.rejected(doc)
    def test_valid_zero_volume_retains_research_quality(self):
        doc=self.doc();doc['results'][0]['v']=0;d=self.result(doc)
        self.assertEqual(d.payload['bars'][0]['volume'],0);self.assertEqual(d.entitlement,'DELAY_UNVERIFIED');self.assertEqual(d.quality,'DATA_INCOMPLETE')

if __name__=='__main__':unittest.main()
