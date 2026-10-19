process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {parse}=require('./commands.cjs');
const make=(text)=>({update_id:7,message:{date:1000,chat:{id:42,type:'private'},from:{id:42},text}});
test('only paired private human may command',()=>{const u=make('/status');assert.equal(parse(u,42,1000).command,'status');assert.equal(parse(u,43,1000),null);u.message.from.id=43;assert.equal(parse(u,42,1000),null);u.message.from.id=42;u.message.chat.type='group';assert.equal(parse(u,42,1000),null)});
test('old future forwarded and edited updates rejected',()=>{assert.equal(parse(make('/status'),42,1400),null);assert.equal(parse(make('/status'),42,900),null);const u=make('/status');u.message.forward_origin={};assert.equal(parse(u,42,1000),null);assert.equal(parse({update_id:7,edited_message:make('/status').message},42,1000),null)});
test('requests bounded and tokens rejected',()=>{assert.equal(parse(make('/request add a chart'),42,1000).text,'add a chart');assert.equal(parse(make('/request'),42,1000).command,'invalid');assert.equal(parse(make('/request '+ 'x'.repeat(1501)),42,1000).command,'invalid');assert.equal(parse(make('/request 123456789:'+ 'x'.repeat(30)),42,1000).command,'invalid')});
test('unknown trading and shell commands never execute',()=>{assert.equal(parse(make('/buy XYZ'),42,1000).command,'help');assert.equal(parse(make('/exec calc'),42,1000).command,'help')});

test('guest alerts are refused locally for every argument even if Python is unavailable',()=>{
 const {reply,accessReply}=require('./commands.cjs'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),access=require('./access.cjs');
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'ag-auth-')),file=path.join(directory,'access.json');
 try{
  access.join(200,access.issue(file),file);
  for(const text of ['', 'INVALID !', 'ideas on']){
   assert.match(accessReply({command:'alerts',text},200,false,file),/Only the owner/);
   assert.match(reply({command:'alerts',text},'fixture-auth',access.key(200)),/Only the owner/);
  }
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
