const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {validateEvent,sendSingle}=require('./notifier.cjs');
function event(){return {id:'free-fixture',kind:'RESEARCH',tenant:'owner',audience:'PRIVATE',presentation_version:'owner-free-v3',alert_type:'TREND_LINE',text:Array(8).fill('Research fixture; no personal fill').join('\n'),expires_at:new Date(Date.now()+60000).toISOString(),disable_notification:true};}
test('free v3 uses actual silent eight-line payload and no wrapper',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ag-free-'));try{let payload;const e=event();const r=await sendSingle(e,{chat_id:1},dir,async(_,method,p)=>{payload=p;return {message_id:1};});assert.equal(r.status,'TELEGRAM_ACCEPTED');assert.equal(payload.text,e.text);assert.equal(payload.disable_notification,true);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('free v3 does not weaken live-kind, parent, research or line gates',()=>{
 const e=event();assert.ok(validateEvent(e));assert.throws(()=>validateEvent({...e,text:e.text+'\nextra'}),/LINE_LIMIT/);
 for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...e,kind}));
 assert.throws(()=>validateEvent({...e,alert_type:'IDEA_UPDATE'}),/PARENT/);
 const idea={...e,alert_type:'SPY_IDEA',text:'SPY SETUP CONFIRMED · research · ID '+'a'.repeat(24)+' · CALL direction\nENTRY CONFIRMED · fictional\nExperimental · manual review'};
 assert.ok(validateEvent(idea));assert.throws(()=>validateEvent({...idea,text:idea.text.replace('Experimental · manual review','BUY THIS CONTRACT')}),/LABEL/);
});
