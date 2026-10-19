// Real handlers, isolated fixture files, fake Telegram transport. Never loads a vault.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const registry=require('../monitoring/command_registry.cjs'),commands=require('../monitoring/commands.cjs'),access=require('../monitoring/access.cjs');
const {validateEvent}=require('../monitoring/notifier.cjs');
const root=path.resolve(__dirname,'..'),file=path.join(root,'monitoring','access.json');
const code=access.issue(file);access.join(1002,code,file);
assert.ok(access.join(1004,access.issue(file),file));assert.ok(access.revoke(access.key(1004),file));
const expiredInvitation=access.issue(file,1000);assert.equal(access.join(1005,expiredInvitation,file,1000+86400001),false);
const args={help:'all',users:'1',revoke:'a'.repeat(24),trend:'',fill:'cancel',alerts:'',plan:'SPY261014C00500000 499 501 502 60',option_bought:'SPY261014C00500000 1 2.40 0.65 2026-10-08T10:00:00-04:00 FORCE',option_sold:'SPY261014C00500000 1 3.10 0.65 2026-10-08T11:00:00-04:00 FORCE',void:'fixture-seed',request:'Fixture research question',skipped:'fixture-idea',demo:'start',join:'invalid'};
const rows=[];let n=0;
for(const role of ['owner','guest','stranger','revoked','expired_invitation'])for(const command of registry.commands)for(const testArgs of [{variant:'valid',text:args[command.command]||''},{variant:'missing',text:''},{variant:'invalid',text:'INVALID !'}]){
 const sender={owner:1001,guest:1002,stranger:1003,revoked:1004,expired_invitation:1005}[role],isOwner=role==='owner',parsed={command:command.command,text:role==='expired_invitation'&&command.command==='join'&&testArgs.variant==='valid'?expiredInvitation:testArgs.text};
 let result='PASS',notes='',text='';
 try{
  // Fixture member is reinstated after leave/revoke; each command has its own role precondition.
  if(role==='guest'&&!access.member(sender,file)){const invite=access.issue(file);access.join(sender,invite,file);}
  const special=commands.accessReply(parsed,sender,isOwner,file);
  const response=special||commands.reply(parsed,'fixture-'+(++n),isOwner?null:access.key(sender));
  text=typeof response==='string'?response:response.text;
  assert.ok(text&&text.trim());assert.ok(text.length<=3500);
  if(['stranger','revoked','expired_invitation'].includes(role))assert.match(text,/invitation-only/);
  if(role==='guest'&&['users','invite','revoke','alerts'].includes(command.command))assert.match(text,/owner/i);
  assert.ok(!/\b\d{6,}:[A-Za-z0-9_-]{25,}\b/.test(text));
  // Fake transport invokes the exact notifier validator; no HTTPS or credentials.
  validateEvent({id:'verify-'+n,kind:'RESEARCH',text,expires_at:new Date(Date.now()+60000).toISOString()});
 }catch(e){result='FAIL';notes=e.message.slice(0,160);}
 text=text.replace(/\/join\s+\S+/g,'invitation instructions').replace(/\b[a-f0-9]{24,}\b/g,'[EXAMPLE ID]').replace(/\b100[12345]\b/g,'[EXAMPLE ID]').replace(/@\w+/g,'[EXAMPLE name]');
 rows.push({command:command.command,role,arguments:testArgs.variant,result,reply_excerpt:'EXAMPLE — fixture response\n'+text.slice(0,360),notes});
}
for(const owner of [true,false]){
 assert.deepEqual(registry.menu(owner).map(c=>c.command),['trend','score','demo','news','more','help']);
 const joined=registry.help(false,owner)+'\n'+registry.more(owner);
 for(const c of registry.commands.filter(c=>owner||!['users','invite','revoke','alerts'].includes(c.command))){const count=(joined.match(new RegExp('/'+c.command+'(?=\\b)','g'))||[]).length;assert.equal(count,1,c.command+' menu coverage');}
}
console.log(JSON.stringify({rows,menu:registry.menu().map(c=>c.command),command_count:registry.commands.length,roles:['owner','guest','stranger','revoked','expired_invitation'],invitation_proofs:{revoked_member_rejected:!access.member(1004,file),expired_invitation_rejected:!access.member(1005,file)}}));
process.exitCode=rows.some(r=>r.result==='FAIL')?1:0;
