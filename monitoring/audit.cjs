// One immutable file per safe audit event; never log raw commands, tokens or invitation codes.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function audit(kind,actor,details={}){const dir=path.join(__dirname,'../logs/security_audit');fs.mkdirSync(dir,{recursive:true});const id=crypto.randomUUID();fs.writeFileSync(path.join(dir,id+'.json'),JSON.stringify({id,kind,actor,at:new Date().toISOString(),details}),{flag:'wx'});}
module.exports={audit};
