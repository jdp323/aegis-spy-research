// Validate full simulated timelines through the actual notifier with a fake client.
const fs=require('node:fs'),path=require('node:path');
const {validateEvent,send}=require('../monitoring/notifier.cjs');
async function main(){
 const input=JSON.parse(fs.readFileSync(0,'utf8'));let calls=0,events=0;const original=Date.now;
 try{for(const scenario of input.scenarios){
  for(const event of scenario.timeline){
   Date.now=()=>Date.parse(event.at_et);validateEvent(event,Date.now());
   const directory=path.join(input.directory,scenario.name);
   const result=await send(event,{token:'fixture',chat_id:1},directory,async(_,method,payload)=>{
    if(method!=='sendMessage'||payload.chat_id!==1||payload.disable_notification!==event.disable_notification)throw Error('FAKE_TRANSPORT_MISMATCH');
    calls++;return {message_id:calls};
   });
   if(result.status!=='TELEGRAM_ACCEPTED')throw Error('FAKE_TRANSPORT_REJECTED');events++;
  }
 }}finally{Date.now=original;}
 console.log(JSON.stringify({status:'PASS',events,calls,transport:'Actual notifier validator/send with fake client, fake clock, fixture recipient only; no network or vault'}));
}
main().catch(e=>{console.log(JSON.stringify({status:'FAIL',reason:e.message}));process.exitCode=1;});
