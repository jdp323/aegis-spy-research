// Generated outbox events only. Dependencies are checked for each recipient.
const fs=require('node:fs'),path=require('node:path');
const {vault,verified,send}=require('./notifier.cjs'),access=require('./access.cjs');
const {audit}=require('./audit.cjs'),{ordered}=require('./delivery_order.cjs');
const root=path.resolve(__dirname,'..');
function write(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=file+'.tmp-'+process.pid;fs.writeFileSync(tmp,JSON.stringify(value));fs.renameSync(tmp,file);}
function deferred(result){return result.status==='DEFERRED_PARENT_NOT_ACCEPTED'||result.status==='SHARED_SEND_DEFERRED';}
async function dispatchOnce(credentials,options={}){
 const base=options.root||root,sendEvent=options.send||send,clock=options.clock||Date.now;
 const out=path.join(base,'monitoring/outbox'),health=path.join(base,'runtime/dispatcher_health.json');fs.mkdirSync(out,{recursive:true});
 const events=[],names=new Map(),results=[],completed=new Set();
 for(const name of fs.readdirSync(out).filter(name=>name.endsWith('.json'))){
  if(fs.existsSync(path.join(base,'logs/dispatch',name)))completed.add(name);
  try{const event=JSON.parse(fs.readFileSync(path.join(out,name),'utf8'));if(typeof event.id!=='string')throw Error();events.push(event);names.set(event.id,name);}
  catch{if(!completed.has(name))write(path.join(base,'logs/dispatch',name),{status:'NOT_SENT',reason:'INVALID_EVENT_FILE'});}
 }
 let queue,remaining=events;
 while(true){
  try{queue=ordered(remaining).filter(event=>!completed.has(names.get(event.id)));break;}
  catch(error){
   const invalid=new Set(error.event_ids||[]);if(!invalid.size){write(health,{pid:process.pid,at:new Date(clock()).toISOString(),state:'DEPENDENCY_GRAPH_FAILED'});return [{status:'NOT_SENT',reason:'DEPENDENCY_CYCLE'}];}
   for(const id of invalid)if(!completed.has(names.get(id))){write(path.join(base,'logs/dispatch',names.get(id)),{status:'NOT_SENT',reason:'DEPENDENCY_CYCLE'});results.push({id,status:'NOT_SENT',reason:'DEPENDENCY_CYCLE'});}
   remaining=remaining.filter(event=>!invalid.has(event.id));
  }
 }
 const deadline=clock()+(options.budgetMs??30000);let count=0;
 for(const event of queue){
  if(clock()>=deadline||count>=(options.maxEvents??20))break;
  count+=1;
  const name=names.get(event.id),marker=path.join(base,'logs/dispatch',name);let result;
  write(health,{pid:process.pid,at:new Date(clock()).toISOString(),state:'RUNNING',phase:'DISPATCH',pending:queue.length-count+1});
  try{
   let target=credentials;
   if(event.tenant&&event.tenant!=='owner'){
    if(event.audience!=='PRIVATE')throw Error('INVALID_TENANT_AUDIENCE');
    const member=(options.users||access.users)().find(member=>member.id===event.tenant);if(!member?.chat_id)throw Error('NO_ACTIVE_DESTINATION');target={...credentials,chat_id:member.chat_id};
   }
   if(!Number.isFinite(Date.parse(event.expires_at))||Date.parse(event.expires_at)<=clock())throw Error('EXPIRED');
   result=await sendEvent(event,target,path.join(base,'logs/notifications'));
   if(deferred(result))write(path.join(base,'logs/dispatch_deferred',name),{status:result.status,reason:result.reason||'RECIPIENT_PARENT_NOT_ACCEPTED',at:new Date(clock()).toISOString()});
   else{write(marker,result);if(!options.noAudit)audit('alert_delivery','dispatcher',{event_id:event.id,status:result.status});}
  }catch(error){
   result={status:'NOT_SENT_OR_UNCERTAIN',reason:['EXPIRED','NO_ACTIVE_DESTINATION','INVALID_TENANT_AUDIENCE'].includes(error.message)?error.message:'VALIDATION_OR_DELIVERY_FAILED'};
   write(marker,result);
  }
  results.push({id:event.id,...result});
 }
 const waiting=results.filter(deferred).length;
 write(health,{pid:process.pid,at:new Date(clock()).toISOString(),state:'RUNNING',phase:'IDLE',processed:results.length,pending:Math.max(0,queue.length-count)+waiting,deferred:waiting});
 return results;
}
async function run(){
 const credentials=JSON.parse(vault('load'));await verified(credentials);let stopped=false;
 process.on('SIGINT',()=>{stopped=true;});process.on('SIGTERM',()=>{stopped=true;});
 while(!stopped&&!fs.existsSync(path.join(root,'runtime/shutdown.request'))){await dispatchOnce(credentials);await new Promise(resolve=>setTimeout(resolve,2000));}
 write(path.join(root,'runtime/dispatcher_health.json'),{pid:process.pid,at:new Date().toISOString(),state:'STOPPED'});
}
module.exports={dispatchOnce,deferred};
if(require.main===module)run().catch(()=>{console.error('DISPATCHER_STOPPED_NO_SECRETS_LOGGED');process.exitCode=1;});
