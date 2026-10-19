// Authenticated private-chat commands. No shell, code execution, or brokerage actions.
const fs=require('node:fs'),path=require('node:path');
const {vault,verified,api,send}=require('./notifier.cjs');
const ROOT=path.resolve(__dirname,'..');
const {spawnSync}=require('node:child_process');
const registry=require('./command_registry.cjs');
const {audit}=require('./audit.cjs');
const access=require('./access.cjs');
async function pace(throttles,sender,clock=Date.now,sleep=ms=>new Promise(r=>setTimeout(r,ms))){
 const key=String(sender),last=throttles.get(key);
 if(last!==undefined){const delay=1000-(clock()-last);if(delay>0)await sleep(delay);}
 throttles.set(key,clock());if(throttles.size>1000)throttles.delete(throttles.keys().next().value);
}
function parse(update,owner,now=Date.now()/1000){
 const m=update?.message;
 if(!Number.isSafeInteger(update?.update_id)||!m||m.chat?.type!=='private'||String(m.chat.id)!==String(owner)||String(m.from?.id)!==String(owner)||m.from?.is_bot||m.forward_origin||m.forward_date||m.via_bot)return null;
 if(!Number.isFinite(m.date)||now-m.date>300||m.date>now+10||typeof m.text!=='string')return null;
 const match=m.text.trim().match(/^\/([a-z_]+)(?:@([A-Za-z0-9_]{1,32}))?(?:\s+([\s\S]*))?$/i);
 if(match?.[2]&&!require('./bot_identity.cjs').matchesUsername(match[2]))return null;
 if(!match||!registry.knows(match[1].toLowerCase()))return {command:'help',text:''};
 const command=match[1].toLowerCase(),text=(match[3]||'').trim();
 if(command==='request'&&(!text||text.length>1500||/\b\d{6,}:[A-Za-z0-9_-]{25,}\b/.test(text)))return {command:'invalid',text:''};
 return {command,text};
}
function read(file){return JSON.parse(fs.readFileSync(path.join(ROOT,file),'utf8').replace(/^\uFEFF/,''));}
function accessReply(parsed,sender,isOwner,file){
 if(!isOwner&&!access.member(sender,file)){
  if(parsed.command==='join'&&access.join(sender,parsed.text,file))return 'Welcome. Your private access ID: '+access.key(sender)+'. Use /howto or /demo start. You will also receive shared research and general bot updates. Reports and demos are private to each user. Research is experimental; live signals are not ready. /leave disables access.';
  return 'This bot is invitation-only. Ask its owner for a code, then send /join CODE. Never send passwords or bot tokens.';
 }
 if(parsed.command==='alerts'&&!isOwner)return 'Only the owner can inspect or change alert settings.';
 if(parsed.command==='users')return isOwner?access.userList(parsed.text,file):'Only the owner can list users.';
 if(parsed.command==='invite')return isOwner?'One-use invitation, expires in24hours. Share only with your intended recipient:\n/join '+access.issue(file):'Only the owner can create invitations.';
 if(parsed.command==='revoke')return isOwner?(access.revoke(parsed.text,file)?'Guest access revoked.':'Access ID not found.'):'Only the owner can revoke other users.';
 if(parsed.command==='leave')return isOwner?'Owner access cannot be removed here.':(access.revoke(access.key(sender),file)?'Your access is disabled. Stored reports are retained.':'Access already disabled.');
 if(parsed.command==='join')return 'You already have access.';
 return null;
}
function reply(parsed,id,tenant=null){
 // Reject owner-only requests before starting any Python child. Authorization
 // remains explicit even when the local worker is busy or unavailable.
 if(parsed.command==='alerts'&&tenant!==null)return 'Only the owner can inspect or change alert settings.';
 if(['health','feed','trend','details','score','why','fill','alerts','paper','signals','plan','status','news','setup','learn','forecast','premarket','outlook','sentiment','research'].includes(parsed.command)){
  const r=spawnSync(require('./runtime.cjs').python(),['-m','core.bot_commands'],{cwd:ROOT,input:JSON.stringify({...parsed,id,tenant}),encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},windowsHide:true,timeout:['trend','premarket'].includes(parsed.command)?15000:10000});
  if(r.status===0){try{const result=JSON.parse(r.stdout);if(result&&typeof result.text==='string')return result;}catch{}}
 return r.status===0?r.stdout.trim():parsed.command==='trend'?'SPY TREND: refresh did not complete within the command budget. No current direction inferred. Retry /trend after 60 seconds; /news shows saved research.':'Local research status unavailable; no order placed.';
 }
 if(parsed.command==='more')return registry.more(tenant===null);
 if(parsed.command==='howto')return registry.howto();
 if(parsed.command==='help')return registry.help(parsed.text==='all',tenant===null);
 if(parsed.command==='demo')return require('./demo_bridge.cjs').invoke({text:parsed.text,tenant:tenant||'owner'});
 if(['void','option_bought','option_sold','option_positions'].includes(parsed.command)){
  const r=spawnSync(require('./runtime.cjs').python(),['-m','options.command'],{cwd:ROOT,input:JSON.stringify({...parsed,id,tenant}),encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},windowsHide:true,timeout:10000});
  return r.status===0?r.stdout.trim():'Option report could not be processed. No execution was attempted; use /request for review.';
 }
 if(parsed.command==='skipped')return 'Not-purchased report queued for the next review. No holding created.';
 if(parsed.command==='request'&&tenant)return 'Guest request saved privately. It does not control the installation owner or app settings. No immediate personal review is promised.';
 if(parsed.command==='request')return 'Request '+id+' saved for operator review. This application does not run an AI review agent or authorize trades. Contact the installation owner directly for urgent changes.';
 if(parsed.command==='invalid')return 'Use /request followed by 1–1500 characters. Do not send credentials.';
 return registry.help(false,tenant===null);
}
async function run(){
 const credentials=JSON.parse(vault('load'));await verified(credentials);
 const dir=path.join(ROOT,'monitoring/inbox');fs.mkdirSync(dir,{recursive:true});
 const lock=path.join(dir,'listener.lock');
 try{fs.writeFileSync(lock,JSON.stringify({pid:process.pid,started_at:new Date().toISOString()}),{flag:'wx'});}catch{throw Error('LISTENER_LOCK_EXISTS');}
 const cleanup=()=>{try{fs.unlinkSync(lock);}catch{}};
 process.on('exit',cleanup);process.on('SIGINT',()=>process.exit(0));process.on('SIGTERM',()=>process.exit(0));
 let offset=0;
 const cursor=path.join(dir,'cursor.json');
 if(fs.existsSync(cursor))offset=JSON.parse(fs.readFileSync(cursor,'utf8')).offset;
 await api(credentials.token,'setMyCommands',{commands:registry.menu(),scope:{type:'chat',chat_id:credentials.chat_id}});
 await api(credentials.token,'setMyCommands',{commands:registry.menu(false),scope:{type:'all_private_chats'}});
 const throttles=new Map();
 console.log('COMMAND_LISTENER_READY');
 while(!fs.existsSync(path.join(ROOT,'runtime/shutdown.request'))){
  try{
   const updates=await api(credentials.token,'getUpdates',{offset,timeout:10,allowed_updates:['message','callback_query']});
   fs.mkdirSync(path.join(ROOT,'runtime'),{recursive:true});fs.writeFileSync(path.join(ROOT,'runtime/telegram_health.json'),JSON.stringify({state:'RUNNING',pid:process.pid,at:new Date().toISOString()}));
   for(const update of updates){
    const demoAction=require('./demo_bridge.cjs').parse(update,credentials.chat_id,x=>access.member(x),x=>access.key(x));
    if(demoAction){
     await pace(throttles,demoAction.destination);
     const response=require('./demo_bridge.cjs').invoke(demoAction);
     await send({id:'reply-demo-'+update.update_id,kind:'INFO',expires_at:new Date(Date.now()+60000).toISOString(),...response},{...credentials,chat_id:demoAction.destination},demoAction.tenant==='owner'?path.join(ROOT,'logs/notifications'):path.join(ROOT,'logs/notifications/guests',demoAction.tenant));
     await api(credentials.token,'answerCallbackQuery',{callback_query_id:demoAction.callback_id,text:'Demo only; nothing real.'});
     offset=Math.max(offset,update.update_id+1);const temp=cursor+'.tmp';fs.writeFileSync(temp,JSON.stringify({offset}));fs.renameSync(temp,cursor);continue;
    }
    const callback=require('./paper_callbacks.cjs').parseCallback(update,credentials.chat_id);
    if(callback){
     await pace(throttles,credentials.chat_id);
     if(require('./paper_callbacks.cjs').parseCallback(update,credentials.chat_id)){
      const r=spawnSync(require('./runtime.cjs').python(),['-m','core.paper_actions'],{cwd:ROOT,input:JSON.stringify(callback),encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},windowsHide:true,timeout:10000});
      let response;try{response=r.status===0?JSON.parse(r.stdout):{text:'Paper action unavailable.'};}catch{response={text:'Paper action unavailable.'};}
      await send({id:'reply-callback-'+update.update_id,kind:'RESEARCH',expires_at:new Date(Date.now()+60000).toISOString(),text:'AEGIS — SPY SETUP (PAPER / UNVALIDATED)\n'+response.text+'\nAEGIS does not place orders. Manual review only.',...(response.photo?{photo:response.photo}:{})},credentials);
      await api(credentials.token,'answerCallbackQuery',{callback_query_id:callback.callback_id,text:'Paper action processed; no order.'});
     }
     offset=Math.max(offset,update.update_id+1);const temp=cursor+'.tmp';fs.writeFileSync(temp,JSON.stringify({offset}));fs.renameSync(temp,cursor);continue;
    }

    const sender=update?.message?.from?.id;
    const parsed=sender?parse(update,sender):null;
    const isOwner=String(sender)===String(credentials.chat_id);
    let special=null;
    
    if(parsed){
     await pace(throttles,sender);
     if(!parse(update,sender)){offset=Math.max(offset,update.update_id+1);continue;}
     const notification=path.join(ROOT,'logs/notifications',...(isOwner?[]:['guests',access.key(sender)]),'reply-telegram-'+update.update_id+'.json');
     const legacyNotification=path.join(ROOT,'logs/notifications','reply-telegram-'+update.update_id+'.json');
     if(fs.existsSync(notification)||(!isOwner&&fs.existsSync(legacyNotification))){offset=Math.max(offset,update.update_id+1);continue;}
     special=accessReply(parsed,sender,isOwner);
    }
    if(parsed&&!isOwner&&access.member(sender))access.touch(sender,undefined,update.message.from);
    if(parsed){
     const id='telegram-'+update.update_id;
     audit('authenticated_command',isOwner?'owner':access.key(sender),{id,command:parsed.command,authorized:isOwner||access.member(sender)});
     const tenant=isOwner?null:access.key(sender);
     const userDir=tenant?path.join(ROOT,'monitoring/users',tenant):dir;
     if(!special)fs.mkdirSync(userDir,{recursive:true});
     fs.mkdirSync(path.join(ROOT,'runtime'),{recursive:true});fs.writeFileSync(path.join(ROOT,'runtime/telegram_health.json'),JSON.stringify({state:'RUNNING',pid:process.pid,at:new Date().toISOString()}));
     const file=path.join(userDir,id+'.json');
     if(!special&&!fs.existsSync(file)){
      fs.writeFileSync(file,JSON.stringify({id,received_at:new Date().toISOString(),command:parsed.command,text:['request','bought','sold','skipped','option_bought','option_sold'].includes(parsed.command)?parsed.text:'',status:['request','bought','sold','skipped','option_bought','option_sold'].includes(parsed.command)?'PENDING_REVIEW':'HANDLED',origin:isOwner?'PAIRED_PRIVATE_TELEGRAM_USER':'INVITED_GUEST_REQUEST_NOT_OWNER_AUTHORITY',scope:'Research/app feedback and manual position reports only; never broker execution, credentials, external sharing or risk-limit authorization'},null,2),{flag:'wx'});
     }
     const response=special||reply(parsed,id,tenant);
     await send({id:'reply-'+id,kind:'INFO',expires_at:new Date(Date.now()+60000).toISOString(),...(typeof response==='string'?{text:response}:response)},{...credentials,chat_id:sender},isOwner?path.join(ROOT,'logs/notifications'):path.join(ROOT,'logs/notifications/guests',access.key(sender)));
    }
    offset=Math.max(offset,update.update_id+1);
    const temp=cursor+'.tmp';fs.writeFileSync(temp,JSON.stringify({offset}));fs.renameSync(temp,cursor);
   }
  }catch{console.error('COMMAND_POLL_FAILED: no secrets logged; retry in 15 seconds.');await new Promise(r=>setTimeout(r,15000));}
 }
}
module.exports={parse,reply,pace,accessReply};
if(require.main===module)run().catch(()=>{console.error('COMMAND_LISTENER_STOPPED: check configuration or existing listener lock. No secrets logged.');process.exitCode=1;});
