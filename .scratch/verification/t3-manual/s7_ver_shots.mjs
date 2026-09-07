// T3 截图 7: 带版本号重截关键页 (import/diag/topo/tl/nodes 首页态)
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
const BASE = 'http://localhost:8720/';

let p = await openTab(BASE + '#import');
await sleep(3500);
const ver = await p.ev(`document.getElementById('sb')?.parentElement?.innerText.match(/v[\\d.]+/) || document.body.innerText.match(/v1\\.0\\.2/)?.[0] || ''`);
console.log('顶栏版本:', ver);
await p.shot(D + 'import_main.jpg');
await p.close();

p = await openTab(BASE + '#diag');
await sleep(15000);
await p.shot(D + 'diag_detect2.jpg');
await p.ev(`(function(){var t=document.querySelector('.sc-view-tab[data-v="learn"]');if(t)t.click();return 1;})()`);
await sleep(4500);
await p.shot(D + 'diag_learn2.jpg');
await p.close();

p = await openTab(BASE + '#topo');
await sleep(15000);
await p.shot(D + 'topo_main.jpg');
await p.close();

p = await openTab(BASE + '#tl');
await sleep(6000);
await p.shot(D + 'timeline_main.jpg');
const row = await p.ev(`(function(){
  var rows=[...document.querySelectorAll('tbody tr')];
  if(rows.length){rows[3].click(); return 'ok';} return 'none';})()`);
await sleep(2500);
await p.shot(D + 'timeline_detail.jpg');
await p.close();

p = await openTab(BASE + '#nodes');
await sleep(4500);
await p.shot(D + 'nodes_main.jpg');
await p.ev(`(function(){ var rows=[...document.querySelectorAll('tr.nd-row')];
  for(var tr of rows){ if((tr.innerText||'').includes('838D')){ tr.click(); break; } } return 1;})()`);
await sleep(2500);
await p.shot(D + 'nodes_expand2.jpg');
await p.close();
console.log('s7 done');
