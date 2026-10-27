const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {sendSingle,send,entryCheck,validateEvent,deliveryError}=require('./notifier.cjs');
const access=require('./access.cjs');
function event(id='entry'){return {id,kind:'RESEARCH',tenant:'owner',audience:'PRIVATE',alert_type:'SPY_IDEA',presentation_version:'owner-compact-v2',text:'CALL RESEARCH · ID '+'a'.repeat(24)+'\nENTRY CONFIRMED · fictional fixture\nExperimental · manual review',expires_at:new Date(Date.now()+60000).toISOString(),entry_guard:{version:'entry-publication-v1'}};}
test('missing publication guard fails closed before production process or transport',async()=>{
 assert.equal(entryCheck(null).eligible,false);const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ag-master-'));try{let calls=0;const e=event();delete e.entry_guard;const r=await sendSingle(e,{},dir,async()=>{calls++;return {message_id:1};});assert.equal(r.reason,'PUBLICATION_GUARD_REQUIRED');assert.equal(calls,0);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('each recipient and definitive retry rechecks proposal; no uncertain replay',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ag-master-')),file=path.join(dir,'access.json');try{
  access.join(2,access.issue(file),file);let checks=0,calls=0;
  // INFO generic shared routing bypasses none: configure actual research sharing
  // only in the isolated suite tree, restoring it in finally.
  const config=path.resolve(__dirname,'../config/upgrade.json'),before=fs.readFileSync(config);try{
   const c=JSON.parse(before);c.signals={...c.signals,shared:true};fs.writeFileSync(config,JSON.stringify(c));
   const r=await send({...event(),audience:'SHARED'},{chat_id:1},path.join(dir,'receipts'),async()=>{calls++;return {message_id:calls};},file,{entryCheck:()=>({eligible:++checks===1,reason:'NO_CHASE_LIMIT_EXCEEDED'})});
   assert.equal(checks,2);assert.equal(calls,1);assert.equal(r.results[1].reason,'NO_CHASE_LIMIT_EXCEEDED');
  }finally{fs.writeFileSync(config,before);}
  let retryChecks=0;const r=await sendSingle(event('retry'),{},dir,async()=>{throw deliveryError('TELEGRAM_REJECTED',{definitive:true});},{sleep:async()=>{},entryCheck:()=>({eligible:++retryChecks===1,reason:'ENTRY_EXPIRED'})});assert.equal(retryChecks,2);assert.equal(r.reason,'ENTRY_EXPIRED');
  let uncertainChecks=0;const opts={entryCheck:()=>{uncertainChecks++;return {eligible:true};}};await sendSingle(event('uncertain'),{},dir,async()=>{throw deliveryError('TIMEOUT');},opts);await sendSingle(event('uncertain'),{},dir,async()=>assert.fail('no resend'),opts);assert.equal(uncertainChecks,1);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('v2 retains concise limits and live kinds stay blocked',()=>{
 const e={...event(),alert_type:'PREOPEN',text:Array(8).fill('fixture').join('\n')};assert.ok(validateEvent(e));assert.throws(()=>validateEvent({...e,text:e.text+'\nextra'}),/LINE_LIMIT/);
 for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...e,kind}));
});
test('notifier check CLI uses verified bot identity with fake read-only API and vault',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ag-cli-'));try{
  const preload=path.join(dir,'fixture.cjs');fs.writeFileSync(preload,`
const cp=require('node:child_process'),https=require('node:https'),{EventEmitter}=require('node:events');
cp.spawnSync=()=>({status:0,stdout:JSON.stringify({token:'12345678:'+ 'z'.repeat(32),chat_id:'123'})});
https.request=(options,callback)=>{const req=new EventEmitter();req.destroy=()=>{};req.end=()=>process.nextTick(()=>{const res=new EventEmitter();res.statusCode=200;callback(res);const result=options.path.endsWith('/getMe')?{id:1,is_bot:true,username:'FixtureResearchBot'}:options.path.endsWith('/getChat')?{id:123,type:'private'}:null;if(!result)throw Error('unexpected API method');res.emit('data',JSON.stringify({ok:true,result}));res.emit('end');});return req;};
`);
  const r=require('node:child_process').spawnSync(process.execPath,['-r',preload,path.resolve(__dirname,'notifier.cjs'),'check'],{encoding:'utf8',timeout:5000,env:{...process.env,AEGIS_TELEGRAM_BOT_USERNAME:'FixtureResearchBot'},windowsHide:true});
  assert.equal(r.status,0,r.stderr);assert.deepEqual(JSON.parse(r.stdout),{status:'READY',bot:'fixtureresearchbot'});
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
