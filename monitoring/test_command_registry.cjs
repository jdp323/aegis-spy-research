process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict');
const registry=require('./command_registry.cjs');const {parse,reply}=require('./commands.cjs');
test('every registered command stays discoverable and parseable; daily menu is concise',()=>{
 const h=registry.help(true),menu=registry.menu();
 assert.equal(new Set(registry.commands.map(c=>c.command)).size,registry.commands.length);
 for(const c of registry.commands){assert.ok(h.includes('/'+c.command));const u={update_id:1,message:{date:100,chat:{id:42,type:'private'},from:{id:42},text:'/'+c.command+' test'}};assert.equal(parse(u,42,100).command,c.command);}
 assert.ok(menu.length<=10);for(const c of ['trend','demo','news','more','help'])assert.ok(menu.some(m=>m.command===c));
 assert.equal(reply({command:'help',text:''},'test'),registry.help());assert.equal(reply({command:'help',text:'all'},'test'),h);assert.equal(reply({command:'start',text:''},'test'),registry.help());assert.ok(h.length<=3500);
 assert.ok(!registry.help().includes('/forecast'));assert.ok(!registry.menu(false).some(c=>['users','invite','revoke'].includes(c.command)));
 assert.ok(!registry.help(true,false).includes('/users'));
});
test('beginner guide and removed share commands stay consistent',()=>{
 assert.equal(reply({command:'howto',text:''},'test'),registry.howto());assert.ok(registry.howto().length<=3500);
 for(const c of ['bought','sold','positions']){assert.equal(registry.knows(c),false);assert.equal(registry.menu().some(x=>x.command===c),false);}
});
