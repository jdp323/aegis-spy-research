// Test-only configuration fixture; no real file/configuration mutation or transport.
const fs=require('node:fs'),path=require('node:path');
const configFile=path.resolve(__dirname,'../config/upgrade.json');
function withSharing(shared,run){
 const original=fs.readFileSync;
 fs.readFileSync=function(file,...args){return typeof file==='string'&&path.resolve(file)===configFile?JSON.stringify({signals:{shared}}):original.call(this,file,...args);};
 const restore=()=>{fs.readFileSync=original;};
 let result;try{result=run();}catch(error){restore();throw error;}
 if(result&&typeof result.then==='function')return result.finally(restore);
 restore();return result;
}
module.exports={withSharing};
