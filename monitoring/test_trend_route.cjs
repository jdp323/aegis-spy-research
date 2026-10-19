process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
test('trend owner and guest use bounded Python refresh route and explicit timeout reply',()=>{
 const realRequire=require('node:module').createRequire(path.join(__dirname,'commands.cjs'));
 let calls=[],failed=false;
 const sandbox={module:{exports:{}},__dirname,process,console,require:name=>name==='node:child_process'?{spawnSync:(exe,args,options)=>{calls.push({exe,args,options});return failed?{status:null}:{status:0,stdout:'SPY TREND: UP\nREFRESH: Fetched for this request.'};}}:realRequire(name)};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'commands.cjs'),'utf8'),sandbox);
 const reply=sandbox.module.exports.reply;
 for(const tenant of [null,'0'.repeat(24)]){
  assert.match(reply({command:'trend',text:''},'trend-fixture',tenant),/Fetched for this request/);
  const c=calls.at(-1);assert.equal(c.options.timeout,15000);assert.equal(c.args[1],'core.bot_commands');assert.equal(JSON.parse(c.options.input).tenant,tenant);assert.equal(JSON.parse(c.options.input).command,'trend');
 }
 failed=true;assert.match(reply({command:'trend',text:''},'trend-timeout'),/did not complete/);
 assert.match(reply({command:'trend',text:''},'trend-timeout'),/after 60 seconds/);
});
