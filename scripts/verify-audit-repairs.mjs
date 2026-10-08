/** Run audit scenarios without treating an exit code of zero as proof of PASS. */
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const files=fs.readdirSync(path.join(root,'scripts')).filter(n=>/^f0[2-9]-/.test(n)&&n.endsWith('.mjs')&&!n.includes('-source-')).sort();
files.push('fix-acceptance.mjs');
let failures=0;
for(const name of files){
 const r=spawnSync(process.execPath,[path.join(root,'scripts',name)],{cwd:root,encoding:'utf8',maxBuffer:32*1024*1024});
 try{
  const result=JSON.parse(r.stdout);
  const count=Number(result.failed||0);
  const ok=r.status===0&&count===0&&result.ok!==false;
  console.log(JSON.stringify({test:name,ok,passed:result.passed,failed:count,exitCode:r.status}));
  if(!ok)failures++;
 }catch(error){console.error(name+': invalid evidence or execution failure');console.error(r.stderr);failures++;}
}
console.log(JSON.stringify({suites:files.length,failedSuites:failures}));
process.exitCode=failures?1:0;
