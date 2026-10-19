process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {withSharing}=require('./sharing_test_fixture.cjs');
const {send,validateEvent}=require('./notifier.cjs'),access=require('./access.cjs');
const event=(type)=>({id:'shared-'+type,kind:'RESEARCH',alert_type:type,audience:'SHARED',tenant:'owner',...(['IDEA_UPDATE','PAPER_UPDATE'].includes(type)?{parent_event_id:'fixture-parent'}:{}),text:'EXAMPLE (PAPER / UNVALIDATED)\nUnvalidated research. You place orders yourself.\nAEGIS does not place orders. Manual review only.',expires_at:new Date(Date.now()+60000).toISOString()});
test('every public market alert fans out identically only when sharing is enabled',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-sharing-')),file=path.join(dir,'access.json'),log=path.join(dir,'receipts');
 for(const id of [200,300])assert.ok(access.join(id,access.issue(file),file));
 // Dependency acceptance is recipient-local; seed the accepted initial idea.
 for(const folder of [log,...[200,300].map(id=>path.join(log,'guests',access.key(id)))]){fs.mkdirSync(folder,{recursive:true});fs.writeFileSync(path.join(folder,'fixture-parent.json'),JSON.stringify({id:'fixture-parent',status:'TELEGRAM_ACCEPTED'}));}
 const calls=[],fake=async(_,method,payload)=>{calls.push(payload);return {message_id:calls.length};};
 const kinds=['PREOPEN','TREND_LINE','SPY_IDEA','IDEA_UPDATE','IDEA_WARNING','RECAP','PAPER_SIGNAL','PAPER_UPDATE'];
 await withSharing(true,async()=>{
  for(const type of kinds){const e=event(type);await send(e,{token:'fixture',chat_id:100},log,fake,file);const last=calls.slice(-3);assert.deepEqual(last.map(p=>String(p.chat_id)),['100','200','300']);assert.equal(new Set(last.map(p=>p.text)).size,1);await send(e,{token:'fixture',chat_id:100},log,fake,file);}
 });
 assert.equal(calls.length,kinds.length*3);
 await withSharing(false,async()=>{for(const type of kinds)await assert.rejects(send({...event(type),id:'blocked-'+type},{token:'fixture',chat_id:100},log,fake,file));});
 assert.equal(calls.length,kinds.length*3);
});
test('sharing keeps private positions/admin replies private and excludes revoked users',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-sharing-private-')),file=path.join(dir,'access.json'),log=path.join(dir,'receipts');
 for(const id of [200,300])assert.ok(access.join(id,access.issue(file),file));
 const calls=[],fake=async(_,method,payload)=>{calls.push(payload);return {message_id:calls.length};};
 await withSharing(true,async()=>{
  for(const id of ['private-position','private-admin','owner-test'])await send({id,kind:'INFO',text:'EXAMPLE PRIVATE',audience:'PRIVATE',tenant:'owner',expires_at:new Date(Date.now()+60000).toISOString()},{token:'fixture',chat_id:100},log,fake,file);
  assert.deepEqual(calls.map(p=>String(p.chat_id)),['100','100','100']);
  access.revoke(access.key(200),file);await send(event('TREND_LINE'),{token:'fixture',chat_id:100},log,fake,file);
  assert.deepEqual(calls.slice(3).map(p=>String(p.chat_id)),['100','300']);
  for(const kind of ['BUY','SELL','TRADE_PROPOSAL'])assert.throws(()=>validateEvent({...event('TREND_LINE'),kind}));
 });
});
