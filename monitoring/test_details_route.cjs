process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const registry=require('./command_registry.cjs'),{parse}=require('./commands.cjs');
test('details joins all retained typed commands while six-entry main menu remains stable',()=>{
 const retained=['help','howto','join','users','invite','revoke','leave','start','status','feed','health','void','trend','why','score','fill','more','alerts','outlook','sentiment','research','signals','setup','learn','forecast','premarket','paper','plan','news','request','demo','option_bought','option_sold','option_positions','skipped'];
 assert.equal(registry.commands.length,36);for(const command of [...retained,'details'])assert.ok(registry.knows(command));
 assert.match(registry.help(true),/\/details/);assert.match(registry.more(false),/\/details/);
 assert.deepEqual(registry.menu().map(row=>row.command),['trend','score','demo','news','more','help']);
 for(const sender of [100,200])assert.equal(parse({update_id:1,message:{date:100,chat:{id:sender,type:'private'},from:{id:sender},text:'/details'}},sender,100).command,'details');
});
test('details uses actual bounded Python route with exact tenant rather than shell or public feed',()=>{
 const realRequire=require('node:module').createRequire(path.join(__dirname,'commands.cjs'));const calls=[];
 const sandbox={module:{exports:{}},__dirname,process,console,require:name=>name==='node:child_process'?{spawnSync:(exe,args,options)=>{calls.push({exe,args,options});return {status:0,stdout:'SPY RESEARCH DETAILS — fixture'};}}:realRequire(name)};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'commands.cjs'),'utf8'),sandbox);
 for(const tenant of [null,'a'.repeat(24)]){
  assert.match(sandbox.module.exports.reply({command:'details',text:''},'fixture-details',tenant),/DETAILS/);
  const row=calls.at(-1);assert.equal(row.options.timeout,10000);assert.equal(row.args[1],'core.bot_commands');assert.equal(JSON.parse(row.options.input).tenant,tenant);
 }
});
