// Credential-safe Telegram sender. No broker access or execution capability.
const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const ROOT = path.resolve(__dirname,'..');
const PYTHON = require('./runtime.cjs').python();
const VAULT = path.join(__dirname,'vault.py');
const identity=require('./bot_identity.cjs');

function vault(mode, input) {
  const r=spawnSync(PYTHON,[VAULT,mode],{input,encoding:'utf8',windowsHide:true,timeout:15000});
  if(r.status!==0) throw new Error('CREDENTIAL_ACCESS_FAILED');
  return r.stdout;
}
function api(token,method,payload={}) {
  return new Promise((resolve,reject)=>{
    const req=https.request({hostname:'api.telegram.org',path:'/bot'+token+'/'+method,
      method:'POST',headers:{'Content-Type':'application/json'},timeout:20000},res=>{
      let body='';res.on('data',x=>body+=x);res.on('end',()=>{
        try{const r=JSON.parse(body);if(r?.ok===true&&r.result!==undefined)resolve(r.result);else if(r?.ok===false&&Number.isInteger(r.error_code))reject(deliveryError('TELEGRAM_REJECTED',{http_status:res.statusCode,telegram_error_code:r.error_code,definitive:true}));else reject(deliveryError('RESPONSE_PARSE',{http_status:res.statusCode}));}
        catch{reject(deliveryError('RESPONSE_PARSE',{http_status:res.statusCode}));}
      });
    });
    req.on('error',e=>reject(deliveryError('NETWORK',{network_type:['ECONNRESET','ECONNREFUSED','ENOTFOUND','ETIMEDOUT','EAI_AGAIN'].includes(e.code)?e.code:'OTHER'})));
    req.on('timeout',()=>{reject(deliveryError('TIMEOUT'));req.destroy();});
    req.end(JSON.stringify(payload));
  });
}
function deliveryError(type,fields={}){const e=new Error(type);Object.assign(e,{failure_class:type,...fields});return e;}
function classify(e){
 const type=['TELEGRAM_REJECTED','NETWORK','TIMEOUT','RESPONSE_PARSE'].includes(e?.failure_class)?e.failure_class:'UNCLASSIFIED_SEND_EXCEPTION';
 return {failure_class:type,http_status:Number.isInteger(e?.http_status)?e.http_status:null,telegram_error_code:Number.isInteger(e?.telegram_error_code)?e.telegram_error_code:null,network_type:['ECONNRESET','ECONNREFUSED','ENOTFOUND','ETIMEDOUT','EAI_AGAIN','OTHER'].includes(e?.network_type)?e.network_type:null,status:e?.definitive===true&&type==='TELEGRAM_REJECTED'?'FAILED_NOT_ACCEPTED':'UNCERTAIN_AFTER_SEND'};
}
async function verified(credentials) {
  if(!credentials || !/^\d+:[A-Za-z0-9_-]{20,}$/.test(credentials.token || '') || !/^\d+$/.test(String(credentials.chat_id)))
    throw new Error('INVALID_CREDENTIAL_FORMAT');
  const me=await api(credentials.token,'getMe');
  identity.trust(me);
  const chat=await api(credentials.token,'getChat',{chat_id:credentials.chat_id});
  if(chat.type!=='private' || String(chat.id)!==String(credentials.chat_id))throw new Error('PRIVATE_DESTINATION_MISMATCH');
}
function validateEvent(event, now=Date.now()) {
  if(!event || !/^[A-Za-z0-9_-]{1,100}$/.test(event.id || ''))throw new Error('INVALID_EVENT_ID');
  if(event.parent_event_id!==undefined&&(!/^[A-Za-z0-9_-]{1,100}$/.test(event.parent_event_id)||event.parent_event_id===event.id))throw new Error('INVALID_PARENT_EVENT_ID');
  if(['IDEA_UPDATE','PAPER_UPDATE'].includes(event.alert_type)&&!event.parent_event_id)throw new Error('PARENT_EVENT_REQUIRED');
  // Actionable trade alerts remain unavailable until the proposal/risk migration is validated.
  if(!['INFO','RESEARCH','INTERVENTION','TEST'].includes(event.kind))throw new Error('TRADE_PROPOSAL_GATE_NOT_READY');
  if(['SPY_IDEA','IDEA_UPDATE','IDEA_WARNING','TREND_LINE','PREOPEN','RECAP'].includes(event.alert_type)){
    if(event.kind!=='RESEARCH'||event.tenant!=='owner')throw new Error('V5_RESEARCH_OWNER_REQUIRED');
    if(event.alert_type==='SPY_IDEA'&&(!event.text?.includes('(PAPER / UNVALIDATED)')||!event.text?.includes('Unvalidated research. You place orders yourself.')))throw new Error('V5_IDEA_LABEL_REQUIRED');
    if(event.alert_type==='IDEA_UPDATE'&&!event.text?.includes('Unvalidated research.'))throw new Error('V5_UPDATE_LABEL_REQUIRED');
    if(event.audience==='SHARED'){
      let c;try{c=JSON.parse(fs.readFileSync(path.join(ROOT,'config/upgrade.json'),'utf8'));}catch{throw new Error('V5_SHARING_NOT_AUTHORIZED');}
      if(c.signals?.shared!==true)throw new Error('V5_SHARING_NOT_AUTHORIZED');
    }
  }
  if(['PAPER_SIGNAL','PAPER_UPDATE'].includes(event.alert_type)){
    if(event.kind!=='RESEARCH'||event.tenant!=='owner'||!event.text?.includes('(PAPER / UNVALIDATED)')||!event.text?.includes('AEGIS does not place orders. Manual review only.'))throw new Error('PAPER_LABEL_OR_OWNER_REQUIRED');
    if(event.audience==='SHARED'){
      let c;try{c=JSON.parse(fs.readFileSync(path.join(ROOT,'config/upgrade.json'),'utf8'));}catch{throw new Error('PAPER_SHARING_NOT_AUTHORIZED');}
      if(c.signals?.shared!==true)throw new Error('PAPER_SHARING_NOT_AUTHORIZED');
    }
  }
  if(typeof event.text!=='string' || !event.text.trim() || event.text.length>3500)throw new Error('INVALID_MESSAGE');
  if(/\b\d{6,}:[A-Za-z0-9_-]{25,}\b/.test(event.text))throw new Error('SECRET_LIKE_CONTENT_BLOCKED');
  if(event.disable_notification!==undefined&&typeof event.disable_notification!=='boolean')throw new Error('INVALID_SILENT_FLAG');
  const expiry=Date.parse(event.expires_at);
  if(!Number.isFinite(expiry) || expiry<=now)throw new Error('EVENT_EXPIRED_OR_MISSING_EXPIRY');
  if(event.reply_markup){
    const rows=event.reply_markup.inline_keyboard;
    const demo=event.text.startsWith('🧪 DEMO — SIMULATED DATA')&&event.text.endsWith('Nothing here is real.')&&event.audience!== 'SHARED';
    const pattern=demo?/^demo:[a-f0-9]{24}:(call|put|swing|no-trade|next|bought|chart|skipped|stop)$/:/^aegis:(skip|chart|log|more):[a-f0-9]{24}$/;
    if(!Array.isArray(rows)||rows.length>2||rows.some(row=>!Array.isArray(row)||row.length>3||row.some(b=>typeof b.text!=='string'||!pattern.test(b.callback_data)||b.url)))throw new Error('INVALID_PAPER_BUTTONS');
  }
  if(event.photo){const p=path.resolve(event.photo),base=path.join(ROOT,'daily_reports','charts')+path.sep;if(!p.startsWith(base)||!p.endsWith('.png')||fs.statSync(p).size>8*1024*1024)throw new Error('INVALID_CHART_PATH');}
  return event;
}
function apiPhoto(token,payload,buffer){
 return new Promise((resolve,reject)=>{
  const boundary='aegis'+crypto.randomBytes(12).toString('hex');const parts=[];
  for(const [k,v] of Object.entries(payload)){parts.push(Buffer.from('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n'));}
  parts.push(Buffer.from('--'+boundary+'\r\nContent-Disposition: form-data; name="photo"; filename="spy-paper.png"\r\nContent-Type: image/png\r\n\r\n'),buffer,Buffer.from('\r\n--'+boundary+'--\r\n'));const body=Buffer.concat(parts);
    const req=https.request({hostname:'api.telegram.org',path:'/bot'+token+'/sendPhoto',method:'POST',headers:{'Content-Type':'multipart/form-data; boundary='+boundary,'Content-Length':body.length},timeout:20000},res=>{let raw='';res.on('data',x=>raw+=x);res.on('end',()=>{try{const r=JSON.parse(raw);if(r?.ok===true&&r.result!==undefined)resolve(r.result);else if(r?.ok===false&&Number.isInteger(r.error_code))reject(deliveryError('TELEGRAM_REJECTED',{http_status:res.statusCode,telegram_error_code:r.error_code,definitive:true}));else reject(deliveryError('RESPONSE_PARSE',{http_status:res.statusCode}));}catch{reject(deliveryError('RESPONSE_PARSE',{http_status:res.statusCode}));}});});
   req.on('error',e=>reject(deliveryError('NETWORK',{network_type:['ECONNRESET','ECONNREFUSED','ENOTFOUND','ETIMEDOUT','EAI_AGAIN'].includes(e.code)?e.code:'OTHER'})));req.on('timeout',()=>{reject(deliveryError('TIMEOUT'));req.destroy();});req.end(body);
 });
}
async function sendSingle(event, credentials, directory=path.join(ROOT,'logs','notifications'), client=api, options={}) {
  validateEvent(event);
  fs.mkdirSync(directory,{recursive:true});
  const record=path.join(directory,event.id+'.json');
  const contentHash=crypto.createHash('sha256').update(JSON.stringify(event)).digest('hex');
  if(fs.existsSync(record))return {status:'ALREADY_RECORDED_NO_RESEND',id:event.id};
  // Old private non-owner replies used the owner receipt directory. Telegram
  // update IDs are globally unique; preserve those reservations across the
  // additive namespace repair. Never use this rule for shared market events.
  if(event.audience!=='SHARED'&&directory.split(path.sep).includes('guests')&&/^reply-(?:telegram|demo)-\d+$/.test(event.id)&&fs.existsSync(path.resolve(directory,'../..',event.id+'.json')))return {status:'LEGACY_RECORDED_NO_RESEND',id:event.id};
  const parent=require('./delivery_order.cjs').dependency(event,directory);
  if(!parent.ready)return {status:'DEFERRED_PARENT_NOT_ACCEPTED',id:event.id,reason:parent.reason};
  // Exclusive create is also the concurrency lock. Crash/timeout stays uncertain; never blind-retry.
  let fd;
  try{fd=fs.openSync(record,'wx');}catch(e){if(e.code==='EEXIST')return {status:'ALREADY_RECORDED_NO_RESEND',id:event.id};throw e;}
  let status={id:event.id,kind:event.kind,alert_type:event.alert_type||null,recipient_role:directory.split(path.sep).includes('guests')?'guest':'owner',content_hash:contentHash,status:'PENDING_OR_UNCERTAIN',created_at:new Date().toISOString(),attempts:0,...(event.parent_event_id?{parent_event_id:event.parent_event_id}:{})};
  fs.writeFileSync(fd,JSON.stringify(status,null,2));fs.closeSync(fd);
  const limit=Math.max(1,Math.min(3,options.maxAttempts||3)),sleep=options.sleep||(ms=>new Promise(r=>setTimeout(r,ms))),clock=options.clock||Date.now;
  for(let attempt=1;attempt<=limit;attempt++){
   if(clock()>=Date.parse(event.expires_at)){status={...status,status:'FAILED_NOT_ACCEPTED',failure_class:'EXPIRED_BEFORE_SEND'};fs.writeFileSync(record,JSON.stringify(status,null,2));return {status:status.status,id:event.id};}
   status.attempts=attempt;fs.writeFileSync(record,JSON.stringify(status,null,2));
   try{
    const payload={chat_id:credentials.chat_id,text:event.text.startsWith('🧪 DEMO — SIMULATED DATA')?event.text:'AEGIS '+event.kind+'\n'+event.text,disable_notification:event.disable_notification===true,...(event.reply_markup?{reply_markup:event.reply_markup}:{})};
    let message;
    if(event.photo){const photo={chat_id:credentials.chat_id,caption:event.text.slice(0,1024)};message=client===api?await apiPhoto(credentials.token,photo,fs.readFileSync(event.photo)):await client(credentials.token,'sendPhoto',photo);}
    else message=await client(credentials.token,'sendMessage',payload);
    status={...status,status:'TELEGRAM_ACCEPTED',message_id:message.message_id,accepted_at:new Date().toISOString()};
    fs.writeFileSync(record,JSON.stringify(status,null,2));
    return {status:status.status,id:event.id,message_id:message.message_id};
   }catch(e){
     const failure=classify(e);status={...status,...failure,failed_at:new Date().toISOString()};fs.writeFileSync(record,JSON.stringify(status,null,2));
     fs.appendFileSync(path.join(directory,'delivery_transitions.jsonl'),JSON.stringify({at:status.failed_at,event_hash:contentHash,status:status.status,attempt,...failure})+'\n');
     if(status.status==='UNCERTAIN_AFTER_SEND')return {status:'DELIVERY_UNCERTAIN_NO_AUTOMATIC_RETRY',receipt_status:status.status,id:event.id};
     const delay=1000*2**(attempt-1);
     if(attempt>=limit||clock()+delay>=Date.parse(event.expires_at))return {status:status.status,id:event.id};
     await sleep(delay);
   }
  }
}
// Broadcast only explicitly classified public content. Private command replies default private.
async function send(event,credentials,directory=path.join(ROOT,'logs','notifications'),client=api,accessFile) {
  validateEvent(event);
  if(event.audience===undefined||event.audience==='PRIVATE')return sendSingle(event,credentials,directory,client);
  if(event.audience!=='SHARED')throw new Error('INVALID_AUDIENCE');
  if(!['INFO','RESEARCH','TEST'].includes(event.kind))throw new Error('SHARED_KIND_NOT_ALLOWED');
  const access=require('./access.cjs');
  const results=[await sendSingle(event,credentials,directory,client)];
  for(const member of access.users(accessFile)) {
    if(!member.chat_id||String(member.chat_id)===String(credentials.chat_id))continue;
    // Revocation is checked again before each destination; IDs are durable per recipient.
    if(!access.member(member.chat_id,accessFile))continue;
    const guestEvent={...event};
    if(guestEvent.reply_markup?.inline_keyboard?.some(row=>row.some(button=>String(button.callback_data||'').startsWith('aegis:'))))delete guestEvent.reply_markup;
    results.push(await sendSingle(guestEvent,{...credentials,chat_id:member.chat_id},path.join(directory,'guests',member.id),client));
  }
  return {status:results.some(result=>result.status==='DEFERRED_PARENT_NOT_ACCEPTED')?'SHARED_SEND_DEFERRED':'SHARED_SEND_COMPLETED',recipients:results.length,results};
}
async function main() {
  const command=process.argv[2];
  if(command==='configure-stdin') {
    let raw='';for await (const chunk of process.stdin){raw+=chunk;if(raw.length>16384)throw new Error('INPUT_TOO_LARGE');}
    const credentials=JSON.parse(raw);await verified(credentials);vault('save',JSON.stringify(credentials));
    console.log(JSON.stringify({status:'ENCRYPTED_CREDENTIAL_CONFIGURED',bot:EXPECTED_BOT}));return;
  }
  const credentials=JSON.parse(vault('load'));
  await verified(credentials);
  if(command==='check'){console.log(JSON.stringify({status:'READY',bot:EXPECTED_BOT}));return;}
  if(command==='send-file'){
    const file=path.resolve(process.argv[3] || '');
    const events=path.join(ROOT,'monitoring','outbox')+path.sep;
    if(!file.startsWith(events))throw new Error('EVENT_MUST_BE_IN_OUTBOX');
    console.log(JSON.stringify(await send(JSON.parse(fs.readFileSync(file,'utf8')),credentials)));return;
  }
  throw new Error('UNKNOWN_COMMAND');
}
module.exports={validateEvent,send,sendSingle,vault,verified,api,deliveryError,classify};
if(require.main===module)main().catch(()=>{console.error('NOTIFIER_FAILED: verify local configuration, event format and connectivity. No secrets logged.');process.exitCode=1;});
