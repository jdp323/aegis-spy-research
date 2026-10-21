const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {validateEvent,sendSingle}=require('./notifier.cjs');
function status(){return {id:'compact-test',kind:'RESEARCH',tenant:'owner',audience:'PRIVATE',presentation_version:'owner-compact-v1',alert_type:'TREND_LINE',text:'11:00 ET · SPY $500.00\nCurrent trend: UP\nNext hour: upward bias\nNew entry: WAIT — setup not confirmed\nResearch · IEX · as of 10:59 ET',expires_at:new Date(Date.now()+60000).toISOString(),disable_notification:true};}
test('actual Telegram payload has five lines, silent, no extra envelope',async()=>{
 const d=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-compact-'));try{
  const e=status();let seen;await sendSingle(e,{chat_id:1},d,async (_,method,p)=>{seen=p;return {message_id:1};});assert.equal(seen.text,e.text);assert.equal(seen.text.split('\n').length,5);assert.equal(seen.disable_notification,true);
 }finally{fs.rmSync(d,{recursive:true,force:true});}
});
test('compact version cannot bypass line limits, research labels or live-kind gate',()=>{
 const e=status();assert.throws(()=>validateEvent({...e,text:e.text+'\nextra'}),/LINE_LIMIT/);
 for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...e,kind}));
 assert.throws(()=>validateEvent({...e,alert_type:'SPY_IDEA',text:'BUY THIS CONTRACT'}),/LABEL_REQUIRED/);
 assert.throws(()=>validateEvent({...e,alert_type:'IDEA_UPDATE'}),/PARENT_EVENT_REQUIRED/);
});
