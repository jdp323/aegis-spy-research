import unittest,math
from datetime import datetime,timezone,timedelta
from options.trade_plan import estimated_bid,exit_conditions,mismatch,sanity
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class PlanTests(unittest.TestCase):
 def test_estimator_signed_theta_against_reference(self):
  # European call Black-Scholes, finite difference Greeks, fixed IV. Synthetic unit test only.
  def price(s,t):
   k=500;v=.2;d1=(math.log(s/k)+.5*v*v*t)/(v*math.sqrt(t));d2=d1-v*math.sqrt(t);cdf=lambda x:.5*(1+math.erf(x/math.sqrt(2)));return s*cdf(d1)-k*cdf(d2)
  s=500;t=7/365;eps=.01;p=price(s,t);delta=(price(s+eps,t)-price(s-eps,t))/(2*eps);gamma=(price(s+eps,t)-2*p+price(s-eps,t))/eps**2;theta=(price(s,t-1e-5)-p)/(1e-5*365)
  c=dict(bid=p,delta=delta,gamma=gamma,theta=theta)
  for move in (.1,1,2):self.assertLess(abs(estimated_bid(c,move,.01)-price(s+move,t-.01/365)),.02)
  self.assertLess(estimated_bid(c,0,.1),p)
 def test_quote_and_greek_rejections(self):
  c=dict(bid=3,ask=2,delta=2,gamma=-1,theta=.1,vega=1,iv=.2,type='C');r=sanity(c,NOW,{})
  self.assertIn('BID_ASK_INVALID',r);self.assertIn('DELTA_IMPLAUSIBLE',r);self.assertIn('GREEK_SIGN_INVALID',r)
 def test_stale_no_option_dollar_exit(self):
  plan=dict(stop_bid=2,t1_bid=3,t2_bid=4,max_hold_until=(NOW+timedelta(hours=1)).isoformat());s=dict(direction='PUT',invalidation=503,t1=498,t2=496)
  r=exit_conditions(plan,s,{},dict(payload={'bid':10},feed_quality='DELAYED'),NOW)
  self.assertIsNone(r['option_bid']);self.assertNotIn('T1_REVIEW',r['conditions'])
