// Only owner callbacks from this bot's labelled paper messages. No guest or broker route.
const identity=require('./bot_identity.cjs');
function parseCallback(update,owner,now=Date.now()/1000){
 const q=update?.callback_query,m=q?.message,f=q?.from;
 if(!Number.isSafeInteger(update?.update_id)||typeof q?.id!=='string'||q.id.length>100||m?.chat?.type!=='private'||String(m.chat.id)!==String(owner)||String(f?.id)!==String(owner)||f?.is_bot||!identity.matchesAuthor(m.from)||m.forward_origin||m.forward_date||m.via_bot||typeof m.text!=='string'||!m.text.includes('(PAPER / UNVALIDATED)')||!Number.isFinite(m.date)||now-m.date>3600||m.date>now+10)return null;
 const match=q.data?.match(/^aegis:(skip|chart|log|more):([a-f0-9]{24})$/);
 return match?{action:match[1],signal_id:match[2],callback_id:q.id,update_id:update.update_id}:null;
}
module.exports={parseCallback};
