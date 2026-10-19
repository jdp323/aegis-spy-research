process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {reply}=require('./commands.cjs');
test('Python status and news replies preserve UTF-8 and use fresh-data gates',()=>{
 const status=reply({command:'status'},'fixture-readonly');
 assert.match(status,/AEGIS STATUS —/);assert.match(status,/Automatic public research/);assert.ok(!status.includes('\uFFFD'));
 const news=reply({command:'news'},'fixture-readonly');
 assert.match(news,/no option trade instruction/);assert.match(news,/Delay UNVERIFIED/);assert.match(news,/BIAS:/);assert.ok(!news.includes('\uFFFD'));
});
