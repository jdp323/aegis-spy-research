process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),a=require('./access.cjs');
test('member profile capture, identity binding, update and bounded pagination',()=>{
 const file=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'aegis-profile-')),'access.json');
 for(let id=1;id<=6;id++){a.join(id,a.issue(file),file);a.touch(id,file,{id,first_name:'Alice\nName',last_name:'X'.repeat(300),username:'alice_test'});}
 assert.equal(a.users(file)[0].name.includes('\n'),false);assert.ok(a.userList('',file).includes('@alice_test'));assert.ok(a.userList('',file).length<3500);assert.ok(a.userList('2',file).includes('page 2/2'));
 const before=a.users(file)[0].name;a.touch(1,file,{id:2,first_name:'Imposter'});assert.equal(a.users(file)[0].name,before);
 a.touch(1,file,{id:1,first_name:'New Name'});assert.equal(a.users(file)[0].name,'New Name');assert.equal(a.users(file)[0].username,'');
 a.touch(999,file,{id:999,first_name:'Unknown'});assert.equal(a.users(file).length,6);
 assert.ok(a.userList('',file).includes('Last bot message (UTC):'));assert.ok(!a.userList('',file).includes('phone'));
});
