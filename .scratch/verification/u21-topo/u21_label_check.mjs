// U21-3: 标签外侧断言 (横向/纵向两分支都要覆盖) — 用户反馈"地址显示在节点图标内部"的回归测试
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(900); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
console.log('加载:', JSON.stringify(st));
const g = await p.ev(P.geo);
console.log('分支覆盖: 横向 ' + g.branchH + ' / 纵向 ' + g.branchV + ' | 外侧 ' + g.lblOut + ' | 违规 ' + JSON.stringify(g.lblOutBad));
check('标签全部在节点外侧 (无压进图标)', g.lblOutBad.length === 0, JSON.stringify(g.lblOutBad.slice(0,5)));
check('横向分支有覆盖 (cos 大的节点)', g.branchH > 0 || st.nodes <= 2, '横向 ' + g.branchH);
check('纵向分支有覆盖', g.branchV > 0 || st.nodes <= 2, '纵向 ' + g.branchV);
check('标签互不重叠', g.lblOv === 0, String(g.lblOv));
await p.shot('u21_label_check.jpg');
const ex=p.exceptions.length; check('无异常', ex===0, String(ex));
const ok = summary(); await p.close(); process.exit(ok?0:1);
