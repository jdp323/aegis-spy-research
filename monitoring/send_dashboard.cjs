// Sends only the reviewed dashboard screenshot to the existing paired private chat.
const fs=require('node:fs'),path=require('node:path'),https=require('node:https'),crypto=require('node:crypto');
const {vault,verified}=require('./notifier.cjs');
async function main(){
 const root=path.resolve(__dirname,'..');
 const photo=fs.readFileSync(path.join(root,'dashboard/dashboard-preview.jpg'));
 if(photo.length>10000000||photo.subarray(0,3).toString('hex')!=='ffd8ff')throw Error('INVALID_IMAGE');
 const hash=crypto.createHash('sha256').update(photo).digest('hex');
 const record=path.join(root,'logs/notifications/dashboard-'+hash.slice(0,20)+'.json');
 if(fs.existsSync(record)){console.log('ALREADY_RECORDED_NO_RESEND');return;}
 const credentials=JSON.parse(vault('load'));await verified(credentials);
 const boundary='AEGIS'+crypto.randomBytes(16).toString('hex');
 const caption='AEGIS dashboard snapshot — Oct 4, 2026, Eastern time. Tap the image to zoom. The localhost link works only on the computer; Telegram updates and screenshots work on your phone. Research is active; no actionable trade proposal is ready yet.';
 const fields={chat_id:credentials.chat_id,caption};
 const chunks=Object.entries(fields).map(([k,v])=>Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`));
 chunks.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="photo"; filename="aegis-dashboard.jpg"\r\nContent-Type: image/jpeg\r\n\r\n`),photo,Buffer.from(`\r\n--${boundary}--\r\n`));
 const body=Buffer.concat(chunks);
 fs.writeFileSync(record,JSON.stringify({status:'PENDING_OR_UNCERTAIN',kind:'DASHBOARD_SCREENSHOT',hash}),{flag:'wx'});
 const result=await new Promise((resolve,reject)=>{
   const req=https.request({hostname:'api.telegram.org',path:'/bot'+credentials.token+'/sendPhoto',method:'POST',timeout:20000,headers:{'Content-Type':'multipart/form-data; boundary='+boundary,'Content-Length':body.length}},res=>{let data='';res.on('data',x=>data+=x);res.on('end',()=>{try{const r=JSON.parse(data);if(r.ok)resolve({status:'TELEGRAM_ACCEPTED',message_id:r.result.message_id});else reject(Error('REJECTED'));}catch{reject(Error('FAILED'));}})});
   req.on('error',()=>reject(Error('NETWORK_FAILURE')));req.on('timeout',()=>req.destroy());req.end(body);
 });
 fs.writeFileSync(record,JSON.stringify({...result,kind:'DASHBOARD_SCREENSHOT',hash,accepted_at:new Date().toISOString()}));
 console.log(JSON.stringify(result));
}
main().catch(()=>{console.error('DASHBOARD_SEND_FAILED_OR_UNCERTAIN: inspect existing delivery before retrying. No secrets logged.');process.exitCode=1});
