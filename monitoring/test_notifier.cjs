process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {validateEvent,send}=require('./notifier.cjs');
const event=()=>({id:'test',kind:'TEST',text:'Synthetic test',expires_at:new Date(Date.now()+60000).toISOString()});
test('expired and missing expiry are blocked',()=>{
  assert.throws(()=>validateEvent({...event(),expires_at:'2000-01-01'}));
  assert.throws(()=>validateEvent({...event(),expires_at:null}));
});
test('buy sell alerts are blocked pending risk integration',()=>{
  for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...event(),kind}));
});
test('secret-like payload is blocked',()=>assert.throws(()=>validateEvent({...event(),text:('123456789'+':'+'abcdefghijklmnopqrstuvwxyz123456789')})));
test('successful send is never duplicated',async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-notify-test-'));let calls=0;
  const client=async()=>{calls++;return {message_id:1}};
  const e=event();await send(e,{},dir,client);const second=await send(e,{},dir,client);
  assert.equal(calls,1);assert.equal(second.status,'ALREADY_RECORDED_NO_RESEND');
});
test('unknown delivery is not retried automatically',async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-notify-test-'));let calls=0;
  const client=async()=>{calls++;throw new Error('synthetic timeout')};
  const e=event();assert.equal((await send(e,{},dir,client)).status,'DELIVERY_UNCERTAIN_NO_AUTOMATIC_RETRY');
  await send(e,{},dir,client);assert.equal(calls,1);
});
