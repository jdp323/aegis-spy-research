process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {send,validateEvent}=require('./notifier.cjs');
const {withSharing}=require('./sharing_test_fixture.cjs');
const paper=()=>({id:'paper-test',kind:'RESEARCH',alert_type:'PAPER_SIGNAL',audience:'PRIVATE',tenant:'owner',text:'AEGIS — SPY SETUP (PAPER / UNVALIDATED)\nTEST synthetic.\nAEGIS does not place orders. Manual review only.',expires_at:new Date(Date.now()+60000).toISOString()});
test('paper uses research; live kinds remain blocked and shared paper disabled',()=>{
 for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...paper(),kind}));
 withSharing(false,()=>assert.throws(()=>validateEvent({...paper(),audience:'SHARED'})));withSharing(true,()=>assert.ok(validateEvent({...paper(),audience:'SHARED'})));assert.throws(()=>validateEvent({...paper(),tenant:'guest'}));assert.throws(()=>validateEvent({...paper(),text:'no label'}));
});
test('paper fake transport reaches only owner and never resends',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-paper-test-'));const ids=[];const fake=async(t,m,p)=>{ids.push(p.chat_id);return {message_id:1};};
 await send(paper(),{chat_id:100},dir,fake);await send(paper(),{chat_id:100},dir,fake);assert.deepEqual(ids,[100]);
});
