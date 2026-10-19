// Demo-only Python flow. No vault, brokerage client or notification broadcast.
const {spawnSync}=require('node:child_process'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..');
function invoke(data){const r=spawnSync(require('./runtime.cjs').python(),['-X','utf8','-m','ops.demo'],{cwd:ROOT,input:JSON.stringify(data),encoding:'utf8',windowsHide:true,timeout:15000,env:{...process.env,PYTHONIOENCODING:'utf-8'}});try{if(r.status===0)return JSON.parse(r.stdout);}catch{}return {text:'🧪 DEMO — SIMULATED DATA\nDemo unavailable; /demo start retries. No real ledger changed.\nNothing here is real.'};}
function parse(update,owner,member,key,now=Date.now()/1000){
 const c=update?.callback_query,m=c?.message;
 if(!Number.isSafeInteger(update?.update_id)||!c||!m||m.chat?.type!=='private'||String(m.chat.id)!==String(c.from?.id)||c.from?.is_bot||m.forward_origin||m.via_bot||!require('./bot_identity.cjs').matchesAuthor(m.from)||!Number.isFinite(m.date)||now-m.date>300||m.date>now+10)return null;
 const isOwner=String(c.from.id)===String(owner);if(!isOwner&&!member(c.from.id))return null;
 const match=String(c.data||'').match(/^demo:([a-f0-9]{24}):(call|put|swing|no-trade|next|bought|chart|skipped|stop)$/);if(!match)return null;
 return {tenant:isOwner?'owner':key(c.from.id),nonce:match[1],text:match[2],callback_id:String(c.id),destination:c.from.id};
}
module.exports={invoke,parse};
