const fs=require('node:fs'),path=require('node:path');
const DEFAULT=path.join(__dirname,'demo_state.json');
function demo(input='',file=DEFAULT){
 const command=input.trim().toLowerCase()||'start';
 const state=fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):{stage:'IDLE'};
 const prefix='SIMULATION ONLY — fictional Monday session, prices, contract and fills. Not a trade recommendation.\n\n';
 function save(stage){const tmp=file+'.tmp';fs.writeFileSync(tmp,JSON.stringify({stage,updated_at:new Date().toISOString(),simulation:true}));fs.renameSync(tmp,file);}
 if(command==='start'){
  save('IDEA');return prefix+'09:45 ET — EXAMPLE IDEA\nSPY call, hypothetical expiration2026-10-09, strike600. This example contract is not verified as listed.\nInvented SPY trigger: completed5m close above600.50 followed by a retest holding600.50.\nExample premium limit1.50 USD/share; one standard100-share contract would cost150 USD plus fees. Not a sizing recommendation.\nPremium target1.80; thesis invalidation below SPY599.50; planned time exit11:00 ET. Underlying trigger does not guarantee an option fill or cap the loss. Long option can lose its full premium.\nExample expires09:47 ET; do not chase.\nDid you buy? Reply /demo bought to simulate a fill, or /demo skipped. Do NOT use /option_bought for this demonstration.';
 }
 if(command==='bought'){
  if(state.stage!=='IDEA')return prefix+'No open demo idea. Use /demo start to begin again, or /demo status.';
  save('HOLDING');return prefix+'Simulated fill:1 contract at1.50 USD/share, fee0.65 USD. Total cost150.65 USD.\nNo actual position was recorded.\nReply /demo status for a hypothetical10:15 review, then /demo exit for the exit example.';
 }
 if(command==='status'){
  if(!['HOLDING','EXIT_REVIEW'].includes(state.stage))return prefix+'Demo state: '+state.stage+'. Use /demo start to begin.';
  return prefix+'10:15 ET — HOLD-REVIEW EXAMPLE\nInvented option bid1.65; SPY601.20. Gross unrealized P/L15 USD for1 contract; after entry fee14.35 USD, before exit fees.\nHypothetical thesis still intact. Target1.80; underlying invalidation599.50; time exit11:00 ET.\nIn real operation each review must show quote timestamp/source and monitoring limitations. The current app cannot supply continuous exit alerts.\nReply /demo exit.';
 }
 if(command==='exit'){
  if(!['HOLDING','EXIT_REVIEW'].includes(state.stage))return prefix+'First use /demo start and /demo bought.';
  save('EXIT_REVIEW');return prefix+'10:40 ET — EXIT-REVIEW EXAMPLE\nInvented option bid1.80: the illustrative target is reached. Review the price before deciding whether to close. No order is sent.\nDid you sell? Reply /demo sold. This records a simulated1.80 fill only. A quote/target is not proof of execution.';
 }
 if(command==='sold'){
  if(state.stage!=='EXIT_REVIEW')return prefix+'No pending demo exit. Use /demo status or /demo start.';
  save('CLOSED');return prefix+'Demo closed: bought1.50, sold1.80 ×100 =30 USD gross gain. Assumed fees0.65 each side =28.70 USD net gain.\nAll results are invented. No real holding, profit or order was created.\nReal controls: /option_bought and /option_sold report actual past fills; /option_positions shows reports; /news shows saved research; /request queues a message for a scheduled review.\n/demo start repeats this walkthrough.';
 }
 if(command==='skipped'||command==='stop'){save('IDLE');return prefix+'Demo stopped. No position created. /demo start restarts it.';}
 return prefix+'Commands: /demo start → /demo bought → /demo status → /demo exit → /demo sold. Or /demo skipped /demo stop.';
}
module.exports={demo};
