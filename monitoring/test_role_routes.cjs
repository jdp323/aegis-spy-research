process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const registry=require('./command_registry.cjs'),access=require('./access.cjs'),{accessReply,parse,reply}=require('./commands.cjs');
test('all registered commands have owner and guest routes without real account effects',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-role-tests-')),file=path.join(dir,'access.json');
 try{
  access.join(200,access.issue(file),file);
  for(const c of registry.commands){
   const request={command:c.command,text:''};
   const update={update_id:1,message:{date:100,from:{id:200,is_bot:false},chat:{id:200,type:'private'},text:'/'+c.command+(c.command==='request'?' check research':'')}};
   assert.equal(parse(update,200,100).command,c.command);
   // Destructive access commands run only against this temporary invitation store.
   const owner=accessReply(request,100,true,file);
   if(['users','invite','revoke','join','leave'].includes(c.command))assert.equal(typeof owner,'string');else assert.equal(owner,null);
   const guest=accessReply(request,200,false,file);
   if(['users','invite','revoke'].includes(c.command))assert.match(guest,/Only the owner/);
   if(c.command==='leave')access.join(200,access.issue(file),file);
  }
  const outsider=accessReply({command:'status',text:''},300,false,file);assert.match(outsider,/invitation-only/);
  assert.match(accessReply({command:'join',text:access.issue(file)},300,false,file),/Welcome/);
  for(const command of ['help','start','howto','status','feed','news','outlook','sentiment','research','signals','setup','learn','forecast','premarket','paper']){
   for(const tenant of [null,access.key(200)]){
    const result=reply({command,text:''},'fixture-readonly-'+command,tenant);assert.equal(typeof result,'string');assert.ok(result.length>0&&result.length<=3500);assert.ok(!result.includes('\uFFFD'));
   }
  }
  // Invalid fill/plan reports are rejected; no imaginary real positions created.
  for(const command of ['option_bought','option_sold','option_positions'])assert.match(reply({command,text:''},'fixture-invalid','../outside'),/Invalid private storage/);
  assert.match(reply({command:'plan',text:''},'fixture-invalid',access.key(200)),/not applied/);
  assert.match(reply({command:'request',text:'check research'},'fixture-request',access.key(200)),/does not control/);
  assert.match(reply({command:'skipped',text:'fixture'},'fixture-skipped',access.key(200)),/No holding created/);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
