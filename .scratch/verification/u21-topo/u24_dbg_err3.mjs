import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
const prev = p.ws.onmessage;
p.ws.onmessage = (e) => { const m = JSON.parse(e.data);
  if (m.method === 'Runtime.consoleAPICalled') {
    console.log('CONSOLE:', (m.params.args || []).map(a => a.value || a.description || '').join(' ').slice(0, 400));
  }
  prev(e); };
await sleep(8000);
console.log('state:', JSON.stringify(await p.ev(P.state)));
await p.close(); process.exit(0);
