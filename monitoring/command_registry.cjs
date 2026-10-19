// Register every supported command here: parser, /help and Telegram menu share this list.
const commands=[
 ['help','[all]','Useful commands; all shows advanced tools'],
 ['howto','','Quick guide to trend, morning outlook and news'],
 ['join','INVITATION_CODE','Join using a one-use invitation'],
 ['users','[PAGE_NUMBER]','Owner only: names, usernames, IDs and activity'],
 ['invite','','Owner only: create a 24-hour one-use invitation'],
 ['revoke','ACCESS_ID','Owner only: revoke a guest’s access'],
 ['leave','','Guest: disable your own access; records retained'],
 ['start','','Show help and getting-started commands'],
 ['status','','SPY research readiness and schedule'],
 ['feed','','Provider, connection and freshness health'],
 ['health','','Service health and official calendar coverage/staleness'],
 ['void','EVENT_ID','Append reversal of your own fill report; preserve history'],
 ['trend','[details]','Short gated SPY trend and research idea'],
 ['details','','Horizon, source-time and entry-gate diagnostics'],
 ['why','','Exact checks behind the current verdict'],
 ['score','','Underlying idea outcomes: today, 7 days, 30 days and each setup'],
 ['fill','quantity|premium|fees|time|confirm|cancel VALUE','Answer the current actual-fill question; never submits orders'],
 ['more','','All tools, grouped by purpose'],
 ['alerts','[CATEGORY on|off | setup NAME on|off | silent on|off]','Owner only: categories, setups and silent trends'],
 ['outlook','','Clear SPY bias combining price trend and financial news'],
 ['sentiment','','Wallstreetbets top-post/comment sentiment and access status'],
 ['research','','Advanced saved technical research and data limits'],
 ['signals','','Recent research evaluations and rejections'],
 ['setup','','Latest call/put plan evaluation and exact blockers'],
 ['learn','','Measured trend outcomes and improvement comparison'],
 ['forecast','','Experimental closing-area estimate and limitations'],
 ['premarket','','09:15 ET saved outlook, schedule or separate premarket draft'],
 ['paper','','Separate theoretical trade records'],
 ['plan','OCC_SYMBOL INVALIDATION T1 T2 MAX_HOLD_MINUTES','Your holding: SPY-price review conditions'],
 ['news','','Financial news drivers, direction and source links'],
 ['request','YOUR MESSAGE','Queue research, feedback or a correction'],
 ['demo','start|bought|status|exit|sold|skipped|stop','Interactive fictional walkthrough'],
 ['option_bought','OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE]','Report actual fill; exact duplicates require FORCE'],
 ['option_sold','OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE]','Report actual disposal; exact duplicates require FORCE'],
 ['option_positions','','Show your reported SPY option positions'],
 ['skipped','IDEA-ID','Report that you did not buy an idea']
].map(([command,args,description])=>({command,args,description}));
const main=['trend','score','demo','news','more','help'];
const admin=['users','invite','revoke','alerts'];
function visible(owner=true){return commands.filter(c=>owner||!admin.includes(c.command));}
function help(all=false,owner=true){
 if(all)return 'AEGIS — ALL COMMANDS\n\n'+visible(owner).map(c=>'/'+c.command+(c.args?' '+c.args:'')+' — '+c.description).join('\n')+'\n\nOptions: standard SPY OCC symbol; integer contracts; premium USD/share; fees total USD; actual past fill time with timezone. No command places orders. /request queues for scheduled review. Demo is fictional.';
 return 'AEGIS — MARKET INFORMATION\n\n'+visible(owner).filter(c=>main.includes(c.command)).map(c=>'/'+c.command+' — '+c.description).join('\n')+'\n\nAutomatic morning brief: 09:15 ET on US trading days, if the computer is awake/online.\nCounts describe correlated checks, not prediction odds.\nAdvanced syntax is available by adding all to help';
}
function oldMore(owner=true){return 'AEGIS — MORE\n\nMarket info: /news /sentiment /outlook /premarket\nMy trades: /option_bought /option_sold /option_positions /plan /fill /void /skipped\nPractice: /demo\nResearch & system: /why /trend details /status /feed /health /signals /setup /learn /forecast /paper /research /request'+(owner?'\nOwner admin: /users /invite /revoke /alerts':'')+'\n/help all — syntax and descriptions. No command places orders.';}
function more(owner=true){
 const groups={market:['outlook','sentiment','premarket'],trades:['option_bought','option_sold','option_positions','plan','fill','void','skipped'],system:['details','why','status','feed','health','signals','setup','learn','forecast','paper','research','request','howto','start'],access:['join','leave'],admin:['users','invite','revoke','alerts']};
  return 'AEGIS — MORE\n'+Object.entries(groups).map(([name,names])=>name+': '+visible(owner).filter(c=>names.includes(c.command)&&!main.includes(c.command)).map(c=>'/'+c.command).join(' ')).filter(x=>!x.endsWith(': ')).join('\n')+'\nScore is in the main menu. Alerts: trend_lines or ideas on|off; setup SETUP_NAME on|off; silent on|off. Research only; no orders.';
}
function menu(owner=true){return main.map(name=>visible(owner).find(c=>c.command===name)).map(({command,description})=>({command,description}));}
function knows(command){return commands.some(c=>c.command===command);}
function howto(){return `HOW TO USE AEGIS

1. /trend — Recalculate SPY price direction when you ask. UP means the recent price checks lean upward; DOWN means downward; MIXED means disagreement. Every reply labels its price time and feed. Fresh IEX is one exchange; public bars remain historical.

2. /outlook — Read the price/news bias first, then the main drivers. If price evidence is missing, a news-only outlook is labeled. Reddit never decides the price/news bias.

3. /news — Read major financial and macro headlines, their interpretation, publication times and source links. Sources include Alpaca headlines and public Fed, BLS, BEA and CNBC feeds when accessible. Published releases are not a complete future-event calendar.

4. /sentiment — Read a bounded sample of r/wallstreetbets top daily posts and top comments when authorized Reddit access is configured. Posts can be jokes, stale or manipulated. Missing access is shown explicitly; it is not neutral sentiment.

5. Each US trading morning at 09:15 ET, receive a separate price/news outlook 15 minutes before the open. /premarket retrieves that saved report, explains when it is due, or builds a separate draft from sufficient premarket bars before 09:15. Public bars have unverified delay; a draft never takes the scheduled report's place. Opening price/volume can reverse it. Keep the computer awake and connected.

Counts describe correlated indicators or sampled text checks, not the probability of making money. No command places an order. You decide on every trade. Personal reported fills stay private; shared research goes to invited users.

/paper — separate unvalidated option/share-proxy evidence; no orders. /void EVENT_ID appends a reversal of your own fill report. /option_bought and /option_sold reject exact duplicates unless a separate actual fill is explicitly marked FORCE. Paper alerts are owner-only by default.

/help — useful daily commands. /help all — retained advanced tools, position reports, demo and access management.`;}
module.exports={commands,help,menu,knows,howto,more};
