// Isolated fake transports only. No Telegram credentials, vault or network.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {sendSingle,deliveryError}=require('../monitoring/notifier.cjs');
(async()=>{
 const rows=[];
 for(const type of ['TELEGRAM_REJECTED','TIMEOUT','NETWORK','RESPONSE_PARSE']){
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'aegis-v6-schedule-'));let calls=0;
  try{
   const event={id:'v6-fixture',kind:'TEST',text:'TEST — fake transport only',audience:'PRIVATE',expires_at:new Date(Date.now()+60000).toISOString()};
   const fake=async()=>{calls++;throw deliveryError(type,type==='TELEGRAM_REJECTED'?{definitive:true,http_status:429,telegram_error_code:429}:type==='NETWORK'?{network_type:'ECONNRESET'}:{});};
   await sendSingle(event,{},folder,fake,{sleep:async()=>{}});
   await sendSingle(event,{},folder,fake,{sleep:async()=>{}});
   const receipt=JSON.parse(fs.readFileSync(path.join(folder,event.id+'.json')));
   if(calls!==(type==='TELEGRAM_REJECTED'?3:1))throw Error('RETRY_BOUND_FAILED');
   rows.push({type,calls,status:receipt.status,failure_class:receipt.failure_class,http_status:receipt.http_status??null,network_type:receipt.network_type??null});
  }finally{if(path.dirname(path.resolve(folder))!==path.resolve(os.tmpdir()))throw Error('TEMP_PATH_OUTSIDE_SCOPE');fs.rmSync(folder,{recursive:true,force:true});}
 }
 console.log(JSON.stringify(rows));
})().catch(()=>{console.error('FAKE_TRANSPORT_SIMULATION_FAILED');process.exit(1);});
