process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {dependency,ordered}=require('./delivery_order.cjs');
const {send,sendSingle,deliveryError,validateEvent}=require('./notifier.cjs');
const {dispatchOnce}=require('./dispatch.cjs'),access=require('./access.cjs');
const temporary=()=>fs.mkdtempSync(path.join(os.tmpdir(),'ag-order-'));
const event=(id,parent)=>({id,kind:'TEST',text:'TEST — fake transport only',expires_at:new Date(Date.now()+60000).toISOString(),...(parent?{parent_event_id:parent}:{})});
const record=(directory,id,status)=>{fs.mkdirSync(directory,{recursive:true});fs.writeFileSync(path.join(directory,id+'.json'),JSON.stringify({id,status}));};

test('dependency topology precedes filename order; legacy identity inference is deterministic',()=>{
 const id='a'.repeat(24),parent={...event('v5-idea-'+id+'-spy-ideas-v2-observed'),alert_type:'SPY_IDEA'},child={...event('v5-entry-'+id),alert_type:'IDEA_UPDATE'};
 const result=ordered([child,parent]);assert.equal(result[0].id,parent.id);assert.equal(result[1].parent_event_id,parent.id);
 assert.throws(()=>ordered([event('a','b'),event('b','a')]),/CYCLE/);
 const ambiguous=ordered([child,parent,{...parent,id:parent.id+'-other'}]);assert.equal(ambiguous.find(row=>row.id===child.id).parent_event_id,undefined);
});

test('a shared child requires an accepted parent for that exact recipient; no uncertain resend',async()=>{
 const root=temporary(),file=path.join(root,'access.json'),directory=path.join(root,'receipts');
 try{
  access.join(200,access.issue(file),file);const calls=[];
  const client=async(_,method,payload)=>{calls.push(payload);if(String(payload.chat_id)==='200'&&payload.text.includes('parent'))throw deliveryError('TIMEOUT');return {message_id:calls.length};};
  const parent={...event('parent'),audience:'SHARED',text:'TEST parent'},child={...event('child','parent'),audience:'SHARED',text:'TEST child'};
  await send(parent,{chat_id:100},directory,client,file);
  const first=await send(child,{chat_id:100},directory,client,file);assert.equal(first.status,'SHARED_SEND_DEFERRED');
  assert.equal(calls.filter(row=>row.text.includes('child')).length,1);assert.equal(String(calls.at(-1).chat_id),'100');
  await send(parent,{chat_id:100},directory,client,file);await send(child,{chat_id:100},directory,client,file);assert.equal(calls.length,3);
  assert.equal(fs.existsSync(path.join(directory,'guests',access.key(200),'child.json')),false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('failed or missing parent does not reserve a child or call transport',async()=>{
 const root=temporary();try{let calls=0;const client=async()=>{calls++;return {message_id:1};};
  assert.equal((await sendSingle(event('child','parent'),{},root,client)).reason,'PARENT_RECEIPT_UNAVAILABLE');
  record(root,'parent','FAILED_NOT_ACCEPTED');assert.equal((await sendSingle(event('child','parent'),{},root,client)).reason,'PARENT_FAILED_NOT_ACCEPTED');
  assert.equal(calls,0);assert.equal(fs.existsSync(path.join(root,'child.json')),false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('separate owner confirmation permits only owner dependent update',async()=>{
 const root=temporary();try{
  for(const directory of [root,path.join(root,'guests','a'.repeat(24))]){
   record(directory,'parent','UNCERTAIN_AFTER_SEND');const file=path.join(directory,'parent.json');
   const hash=crypto.createHash('sha256').update('parent.json').update(Buffer.from([0])).update(fs.readFileSync(file)).digest('hex');
   fs.writeFileSync(path.join(directory,'owner_confirmations.jsonl'),JSON.stringify({receipt_hash:hash,status:'CONFIRMED_BY_OWNER'})+'\n');
  }
  assert.equal(dependency(event('child','parent'),root).ready,true);
  assert.equal(dependency(event('child','parent'),path.join(root,'guests','a'.repeat(24))).ready,false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('dispatcher sends initial idea before update and retains deferred updates until expiry',async()=>{
 const root=temporary();try{
  const out=path.join(root,'monitoring/outbox');fs.mkdirSync(out,{recursive:true});
  const initial=event('z-parent'),child=event('a-child','z-parent');
  fs.writeFileSync(path.join(out,'0-child.json'),JSON.stringify(child));fs.writeFileSync(path.join(out,'9-parent.json'),JSON.stringify(initial));
  const calls=[],fake=async(e,c,d)=>sendSingle(e,c,d,async()=>{calls.push(e.id);return {message_id:calls.length};});
  await dispatchOnce({}, {root,send:fake,noAudit:true});assert.deepEqual(calls,['z-parent','a-child']);
  const waiting=event('waiting','never-accepted');fs.writeFileSync(path.join(out,'waiting.json'),JSON.stringify(waiting));
  await dispatchOnce({}, {root,send:fake,noAudit:true});await dispatchOnce({}, {root,send:fake,noAudit:true});
  assert.equal(fs.existsSync(path.join(root,'logs/dispatch/waiting.json')),false);
  assert.equal(fs.existsSync(path.join(root,'logs/dispatch_deferred/waiting.json')),true);
  await dispatchOnce({}, {root,send:fake,noAudit:true,clock:()=>Date.now()+120000});
  assert.equal(JSON.parse(fs.readFileSync(path.join(root,'logs/dispatch/waiting.json'))).reason,'EXPIRED');assert.equal(calls.length,2);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('revocation after accepted parent prevents shared child delivery to former guest',async()=>{
 const root=temporary(),file=path.join(root,'access.json'),directory=path.join(root,'receipts');try{
  access.join(200,access.issue(file),file);const calls=[],client=async(_,method,payload)=>{calls.push(String(payload.chat_id));return {message_id:calls.length};};
  await send({...event('parent'),audience:'SHARED'},{chat_id:100},directory,client,file);access.revoke(access.key(200),file);
  await send({...event('child','parent'),audience:'SHARED'},{chat_id:100},directory,client,file);assert.deepEqual(calls,['100','200','100']);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('dependent alert kinds require a valid distinct parent; live kinds remain forbidden',()=>{
 for(const alert_type of ['IDEA_UPDATE','PAPER_UPDATE'])assert.throws(()=>validateEvent({...event('child'),alert_type}),/PARENT_EVENT_REQUIRED/);
 for(const parent_event_id of ['../elsewhere','child'])assert.throws(()=>validateEvent({...event('child'),parent_event_id}),/INVALID_PARENT/);
 for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...event('child','parent'),kind}));
});

test('a malformed dependency cycle cannot starve independent dispatch work',async()=>{
 const root=temporary();try{
  const out=path.join(root,'monitoring/outbox');fs.mkdirSync(out,{recursive:true});
  for(const row of [event('a','b'),event('b','a'),event('independent')])fs.writeFileSync(path.join(out,row.id+'.json'),JSON.stringify(row));
  const calls=[];await dispatchOnce({}, {root,noAudit:true,send:async row=>{calls.push(row.id);return {status:'TELEGRAM_ACCEPTED'};}});
  assert.deepEqual(calls,['independent']);assert.equal(JSON.parse(fs.readFileSync(path.join(root,'logs/dispatch/a.json'))).reason,'DEPENDENCY_CYCLE');
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('shared guests receive usable text without owner-only action buttons',async()=>{
 const root=temporary(),file=path.join(root,'access.json'),directory=path.join(root,'receipts');try{
  access.join(200,access.issue(file),file);const calls=[],client=async(_,method,payload)=>{calls.push(payload);return {message_id:calls.length};};
  await send({...event('buttons'),audience:'SHARED',reply_markup:{inline_keyboard:[[{text:'Chart',callback_data:'aegis:chart:'+'a'.repeat(24)}]]}},{chat_id:100},directory,client,file);
  assert.ok(calls[0].reply_markup);assert.equal(calls[1].reply_markup,undefined);assert.equal(calls[0].text,calls[1].text);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('private reply namespace repair preserves legacy uncertainty without treating shared owner receipts as guest proof',async()=>{
 const root=temporary(),guest=path.join(root,'guests','a'.repeat(24));try{
  record(root,'reply-telegram-123','PENDING_OR_UNCERTAIN');let calls=0;const client=async()=>{calls++;return {message_id:1};};
  assert.equal((await sendSingle(event('reply-telegram-123'),{},guest,client)).status,'LEGACY_RECORDED_NO_RESEND');assert.equal(calls,0);
  await sendSingle({...event('reply-telegram-123'),audience:'SHARED'}, {},guest,client);assert.equal(calls,1);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
