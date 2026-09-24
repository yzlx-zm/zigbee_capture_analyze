import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
await sleep(6000);
console.log('state:', JSON.stringify(await p.ev(P.state)));
console.log('exceptions:', JSON.stringify(p.exceptions.slice(0,3)));
await p.close(); process.exit(0);
