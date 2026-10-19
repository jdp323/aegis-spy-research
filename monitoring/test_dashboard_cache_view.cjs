process.env.AEGIS_TELEGRAM_BOT_USERNAME ||= 'FixtureResearchBot';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
test('unavailable snapshot clears old dashboard values without inferring a holding closed',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../dashboard/upgrade.html'),'utf8'),nodes=new Map();
 const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'old value',replaceChildren(){this.cleared=true},append(){}});return nodes.get(id)};
 const sandbox={document:{getElementById:node,createElement:()=>({textContent:'',append(){}})},fetch:async()=>({ok:false}),setInterval:()=>0,Date,console};
 vm.runInNewContext(html.match(/<script>([\s\S]*)<\/script>/)[1],sandbox);
 const available=sandbox.snapshotAvailable({snapshot_cache:{state:'REFRESH_OVERDUE',data_available:false,snapshot_as_of:null,evaluated_at:'2026-10-14T15:00:00+00:00'}});
 assert.equal(available,false);assert.equal(node('price').textContent,'UNAVAILABLE');assert.match(node('positions').textContent,/No exit, settlement or closure is inferred/);
 assert.equal(node('frames').cleared,true);assert.equal(node('signals').cleared,true);assert.match(node('cache-status').textContent,/does not grant entry readiness/);
 assert.match(node('cache-status').textContent,/source as-of UNAVAILABLE/);assert.doesNotMatch(node('cache-status').textContent,/1969|1970/);
});
