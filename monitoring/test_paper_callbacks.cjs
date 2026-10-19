process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const test=require('node:test'),assert=require('node:assert/strict');const {parseCallback}=require('./paper_callbacks.cjs');const registry=require('./command_registry.cjs');
function update(){return {update_id:1,callback_query:{id:'one',from:{id:100,is_bot:false},data:'aegis:skip:'+'a'.repeat(24),message:{chat:{id:100,type:'private'},from:{is_bot:true,username:'FixtureResearchBot'},date:1000,text:'AEGIS — SPY SETUP (PAPER / UNVALIDATED)'}}};}
test('only owner human private callbacks from expected bot with signal binding',()=>{
 assert.equal(parseCallback(update(),100,1010).action,'skip');assert.equal(parseCallback(update(),200,1010),null);
 for(const mutate of [u=>u.callback_query.from.is_bot=true,u=>u.callback_query.message.from.username='other',u=>u.callback_query.message.forward_origin={},u=>u.callback_query.data='aegis:chart:bad',u=>u.callback_query.message.date=5000]){const u=update();mutate(u);assert.equal(parseCallback(u,100,1010),null);}
 assert.equal(parseCallback(update(),100,5000),null);
});
test('new command help and FORCE syntax stay discoverable',()=>{assert.ok(registry.knows('void'));assert.ok(registry.knows('health'));assert.match(registry.help(true),/\/void EVENT_ID/);assert.match(registry.help(true),/\[FORCE\]/);});
