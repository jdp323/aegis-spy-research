process.env.AEGIS_TELEGRAM_BOT_USERNAME='FixtureResearchBot';
const test=require('node:test'),assert=require('node:assert/strict');
const identity=require('./bot_identity.cjs');
test('own bot identity controls callbacks',()=>{
 assert.equal(identity.matchesAuthor({is_bot:true,username:'OtherResearchBot'}),false);
 assert.equal(identity.matchesAuthor({is_bot:false,username:'FixtureResearchBot'}),false);
 assert.throws(()=>identity.trust({is_bot:true,id:123,username:'OtherResearchBot'}),/BOT_IDENTITY_MISMATCH/);
 identity.trust({is_bot:true,id:123,username:'FixtureResearchBot'});
 assert.equal(identity.matchesAuthor({is_bot:true,id:123,username:'FixtureResearchBot'}),true);
 assert.equal(identity.matchesAuthor({is_bot:true,id:456,username:'FixtureResearchBot'}),false);
});
