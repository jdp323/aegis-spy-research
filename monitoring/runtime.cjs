// Own installed Python, never a developer's machine-specific executable.
const fs=require('node:fs'),path=require('node:path');
function python(){
 if(process.env.AEGIS_PYTHON)return process.env.AEGIS_PYTHON;
 const root=path.resolve(__dirname,'..');
 for(const candidate of [path.join(root,'.venv','Scripts','python.exe'),path.join(root,'.venv','bin','python')])if(fs.existsSync(candidate))return candidate;
 return process.platform==='win32'?'python':'python3';
}
module.exports={python};
