const fs=require('node:fs'),path=require('node:path');
const DEFAULT=path.join(__dirname,'manual_positions');
function holdings(dir=DEFAULT){
 const book={};if(!fs.existsSync(dir))return book;
 const events=fs.readdirSync(dir).filter(x=>x.endsWith('.json')).map(file=>JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'))).sort((a,b)=>a.recorded_at.localeCompare(b.recorded_at));
 for(const e of events){
  const key=e.symbol+' '+e.currency;
  const p=book[key]||{symbol:e.symbol,currency:e.currency,quantity:0,cost:0};
  if(e.side==='bought'){p.quantity+=e.quantity;p.cost+=e.quantity*e.price;}
  else {p.cost-=p.quantity?e.quantity*p.cost/p.quantity:0;p.quantity-=e.quantity;}
  book[key]=p;
 }return book;
}
function record(side,text,id,dir=DEFAULT){
 const m=text.match(/^([A-Z0-9.^_-]{1,24})\s+(\d+(?:\.\d{1,6})?)\s+(\d+(?:\.\d{1,6})?)\s+(CAD|USD)$/i);
 if(!m)return 'Format: /'+side+' SYMBOL QUANTITY PRICE CAD|USD. Stocks/ETFs only. For options use /request with the full contract details; automatic option tracking is not available.';
 const [symbol,quantity,price,currency]=[m[1].toUpperCase(),Number(m[2]),Number(m[3]),m[4].toUpperCase()];
 if(!Number.isFinite(quantity*price)||quantity<=0||price<=0||quantity>1e9||price>1e9)return 'Quantity and price must be positive finite values.';
 if(!/^[A-Za-z0-9_-]+$/.test(id))throw Error('INVALID_ID');
 fs.mkdirSync(dir,{recursive:true});
 const file=path.join(dir,id+'.json');
 if(fs.existsSync(file))return 'This report was already recorded. No duplicate added.';
 if(side==='sold'&&quantity>(holdings(dir)[symbol+' '+currency]?.quantity||0)+1e-9)return 'Sale exceeds your manually reported holding. Check /positions and report the purchase first.';
 fs.writeFileSync(file,JSON.stringify({side,symbol,quantity,price,currency,recorded_at:new Date().toISOString(),source:'USER_REPORTED_NOT_BROKER_VERIFIED',fees_included:false}),{flag:'wx'});
 return 'Recorded your report: '+side+' '+quantity+' '+symbol+' at '+price+' '+currency+'. Entry/exit price is user-reported, fees excluded. No current market price verified. Position will be checked at scheduled research reviews; no continuous monitoring.';
}
function summary(dir=DEFAULT){const list=Object.values(holdings(dir)).filter(p=>p.quantity>1e-9);return list.length?'Manually reported positions (fees excluded):\n'+list.map(p=>p.symbol+': '+p.quantity+' shares, average entry '+(p.cost/p.quantity).toFixed(4)+' '+p.currency).join('\n')+'\nCurrent prices are not available from this command. Scheduled reviews must verify quote source and time.':'No manually reported open positions. Record a stock/ETF purchase with /bought SYMBOL QUANTITY PRICE CAD|USD.';}
module.exports={record,summary,holdings};
