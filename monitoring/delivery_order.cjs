// Recipient-local dependency checks. Receipt acceptance is not handset delivery.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ACCEPTED=new Set(['TELEGRAM_ACCEPTED','CONFIRMED_BY_OWNER']);
function dependency(event,directory){
 if(!event.parent_event_id)return {ready:true};
 const file=path.join(directory,event.parent_event_id+'.json');let raw,receipt;
 try{raw=fs.readFileSync(file);receipt=JSON.parse(raw.toString('utf8'));}catch{return {ready:false,reason:'PARENT_RECEIPT_UNAVAILABLE'};}
 if(receipt.id!==event.parent_event_id)return {ready:false,reason:'PARENT_RECEIPT_INVALID'};
 if(ACCEPTED.has(receipt.status))return {ready:true};
 // Owner confirmations are separate append-only attestations, never guest proof.
 if(!directory.split(path.sep).includes('guests')){
  const hash=crypto.createHash('sha256').update(path.basename(file)).update(Buffer.from([0])).update(raw).digest('hex');
  try{for(const line of fs.readFileSync(path.join(directory,'owner_confirmations.jsonl'),'utf8').split('\n')){
   let row;try{row=JSON.parse(line);}catch{continue;}
   if(row.receipt_hash===hash&&row.status==='CONFIRMED_BY_OWNER')return {ready:true};
  }}catch{}
 }
 return {ready:false,reason:receipt.status==='FAILED_NOT_ACCEPTED'?'PARENT_FAILED_NOT_ACCEPTED':receipt.status==='UNCERTAIN_AFTER_SEND'?'PARENT_UNCERTAIN_AFTER_SEND':'PARENT_NOT_ACCEPTED'};
}
function ordered(events){
 // Historical V5 records did not carry dependencies. Resolve only an unambiguous
 // initial idea; never use another recipient's receipt as a substitute.
 const initial=new Map();
 for(const event of events){const m=event.id?.match(/^v5-idea-([a-f0-9]{24})-/);if(m){const list=initial.get(m[1])||[];list.push(event.id);initial.set(m[1],list);}}
 const decorated=events.map(event=>{
  if(event.parent_event_id)return event;
  if(event.alert_type==='PAPER_UPDATE'&&/^[a-f0-9]{24}$/.test(event.signal_id||'')&&/^[A-Za-z0-9_-]{1,100}$/.test(event.strategy_version||''))return {...event,parent_event_id:'paper-'+crypto.createHash('sha256').update(event.signal_id+event.strategy_version+'PAPER_SIGNAL').digest('hex').slice(0,32)};
  if(event.alert_type!=='IDEA_UPDATE')return event;
  const match=event.id?.match(/^v5-(?:entry|update)-([a-f0-9]{24})(?:-|$)/),parents=match?initial.get(match[1]):null;
  return parents?.length===1?{...event,parent_event_id:parents[0]}:event;
 });
 const index=new Map(decorated.map(event=>[event.id,event])),done=new Set(),visiting=new Set(),result=[];
 function visit(event){if(done.has(event.id))return;if(visiting.has(event.id)){const error=Error('DEPENDENCY_CYCLE');error.event_ids=[...visiting];throw error;}visiting.add(event.id);const parent=index.get(event.parent_event_id);if(parent)visit(parent);visiting.delete(event.id);done.add(event.id);result.push(event);}
 for(const event of [...decorated].sort((a,b)=>String(a.created_at||'').localeCompare(String(b.created_at||''))||a.id.localeCompare(b.id)))visit(event);
 return result;
}
module.exports={dependency,ordered};
