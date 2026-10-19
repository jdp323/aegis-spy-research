const {audit}=require('./audit.cjs');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const DEFAULT=path.join(__dirname,'access.json');
const digest=x=>crypto.createHash('sha256').update(String(x)).digest('hex');
function key(id){if(!/^\d+$/.test(String(id)))throw Error('INVALID_USER');return digest('telegram:'+id).slice(0,24);}
function read(file){return fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):{invites:{},members:{}};}
function save(s,file){const tmp=file+'.tmp';fs.writeFileSync(tmp,JSON.stringify(s,null,2));fs.renameSync(tmp,file);}
function issue(file=DEFAULT,now=Date.now()){const s=read(file),code=crypto.randomBytes(20).toString('hex');s.invites[digest(code)]={expires:now+86400000};save(s,file);if(file===DEFAULT)audit('invitation_created','owner',{expires:s.invites[digest(code)].expires});return code;}
function join(id,code,file=DEFAULT,now=Date.now()){const s=read(file),k=key(id),h=digest(code);if(s.members[k])return true;if(!s.invites[h]||s.invites[h].expires<=now)return false;delete s.invites[h];s.members[k]={chat_id:String(id),joined_at:new Date(now).toISOString()};save(s,file);if(file===DEFAULT)audit('invitation_redeemed',k,{});return true;}
function member(id,file=DEFAULT){return Boolean(read(file).members[key(id)]);}
function revoke(k,file=DEFAULT){if(!/^[a-f0-9]{24}$/.test(k))return false;const s=read(file),found=Boolean(s.members[k]);delete s.members[k];save(s,file);if(file===DEFAULT)audit('access_revoked',k,{found});return found;}
function clean(value,max){return typeof value==='string'?value.replace(/[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]/g,' ').trim().slice(0,max):'';}
function touch(id,file=DEFAULT,profile=null,seen=true){const s=read(file),k=key(id);if(!s.members[k])return;const m=s.members[k];m.chat_id=String(id);if(profile&&String(profile.id)===String(id)){m.name=[clean(profile.first_name,64),clean(profile.last_name,64)].filter(Boolean).join(' ');m.username=/^[A-Za-z0-9_]{1,32}$/.test(profile.username||'')?profile.username:'';}if(seen)m.last_seen_at=new Date().toISOString();save(s,file);}
function users(file=DEFAULT){return Object.entries(read(file).members).map(([id,m])=>({id,...m}));}
function userList(pageText='',file=DEFAULT){const page=Number(pageText||1);if(!Number.isSafeInteger(page)||page<1)return 'Use /users or /users PAGE_NUMBER.';const all=users(file),pages=Math.max(1,Math.ceil(all.length/5));if(page>pages)return 'No such page. Total pages: '+pages;return 'INVITED USERS — '+all.length+' active; page '+page+'/'+pages+'\n'+all.slice((page-1)*5,page*5).map(m=>'Name: '+(m.name||'pending profile update')+'\nUsername: '+(m.username?'@'+m.username:'not available')+'\nTelegram ID: '+(m.chat_id||'pending next message')+'\nAccess ID: '+m.id+'\nJoined (UTC): '+m.joined_at+'\nLast bot message (UTC): '+(m.last_seen_at||'not recorded')).join('\n\n')+'\nNames are self-reported Telegram profiles, not verified identities.\n/users PAGE_NUMBER for more; /revoke ACCESS_ID removes access.';}
module.exports={key,issue,join,member,revoke,touch,users,userList};
