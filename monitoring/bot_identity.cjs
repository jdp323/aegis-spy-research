// Identity comes from this installation's verified Telegram getMe response.
const fs=require('node:fs'),path=require('node:path');
let verifiedName=null,verifiedId=null;
function configured(){
 let value=process.env.AEGIS_TELEGRAM_BOT_USERNAME||'';
 if(!value){try{value=JSON.parse(fs.readFileSync(path.join(__dirname,'../config/telegram.json'),'utf8')).username||'';}catch{}}
 return /^[A-Za-z0-9_]{5,32}$/.test(value)?value.toLowerCase():null;
}
function username(){return verifiedName||configured();}
function matchesUsername(value){const expected=username();return Boolean(expected&&typeof value==='string'&&value.toLowerCase()===expected);}
function matchesAuthor(author){return Boolean(author?.is_bot&&matchesUsername(author.username)&&(verifiedId===null||String(author.id)===String(verifiedId)));}
function trust(me){
 const expected=configured();
 if(!me?.is_bot||!Number.isSafeInteger(me.id)||!/^[A-Za-z0-9_]{5,32}$/.test(me.username||'')||(expected&&me.username.toLowerCase()!==expected))throw Error('BOT_IDENTITY_MISMATCH');
 verifiedName=me.username.toLowerCase();verifiedId=me.id;
}
module.exports={configured,username,matchesUsername,matchesAuthor,trust};
