process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const access=require('./access.cjs'),{send}=require('./notifier.cjs'),registry=require('./command_registry.cjs');
test('shared delivery, private isolation, deduplication and revoked members',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-shared-')),file=path.join(root,'access.json'),log=path.join(root,'logs');
 for(const id of [200,300])assert.ok(access.join(id,access.issue(file),file));
 const calls=[],client=async(t,m,p)=>{calls.push(p);return {message_id:calls.length};};
 const event={id:'shared-test',kind:'RESEARCH',audience:'SHARED',expires_at:new Date(Date.now()+60000).toISOString(),text:'Public research only'};
 await send(event,{token:'dummy',chat_id:100},log,client,file);
 assert.deepEqual(calls.map(x=>String(x.chat_id)),['100','200','300']);assert.equal(new Set(calls.map(x=>x.text)).size,1);
 await send(event,{token:'dummy',chat_id:100},log,client,file);assert.equal(calls.length,3);
 await send({...event,id:'private-test',audience:undefined,text:'Private position'}, {token:'dummy',chat_id:100},log,client,file);assert.equal(calls.length,4);assert.equal(calls[3].chat_id,100);
 access.revoke(access.key(200),file);
 await send({...event,id:'after-revoke'}, {token:'dummy',chat_id:100},log,client,file);assert.deepEqual(calls.slice(4).map(x=>String(x.chat_id)),['100','300']);
 await assert.rejects(send({...event,id:'bad-kind',kind:'INTERVENTION'}, {token:'dummy',chat_id:100},log,client,file));
 assert.ok(access.userList('',file).includes(access.key(300)));assert.ok(!access.userList('',file).includes(access.key(200)));
 assert.ok(registry.more().includes('/users'));assert.ok(!registry.menu(false).some(x=>x.command==='users'));
});
