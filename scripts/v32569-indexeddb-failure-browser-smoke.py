"""Case 8: real Chromium IndexedDB. Fault injection is on the real IDBObjectStore.put for the app 'state' store
(a write-level failure such as quota/abort); no storage mock replaces IndexedDB. Reload proves the last good state."""
import asyncio,json,os,pathlib,threading,http.server,functools,glob
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a): pass
def chromium():
 p=os.environ.get('CHROMIUM_PATH')
 if p: return p
 c=sorted(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome'))
 return c[0] if c else None
async def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True,executable_path=chromium(),args=['--no-sandbox','--disable-dev-shm-usage'])
   page=await browser.new_page()
   url=f'http://127.0.0.1:{server.server_port}/'
   await page.goto(url,wait_until='domcontentloaded');await page.wait_for_function('typeof DB!=="undefined" && DB.data')
   r=await page.evaluate('''async()=>{
    const out={},check=(v,m)=>{if(!v)throw Error(m)};
    ServerStore.available=false;ServerStore.authenticated=false;
    DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();
    const u={id:'qa-admin',name:'QA',role:'admin',active:true,permissions:{all:true},allowedBranchIds:[]};DB.data.users=[u];Auth.user=u;
    const a=Transactions.addCustomer({name:'عميل سليم A'});
    const s1=await DB.save(false);check(s1.indexedDb===true,'baseline save must succeed on real IndexedDB');
    check((await DataStore.localGet()).customers.some(x=>x.id===a.id),'A durable');
    out.aId=a.id;
    const orig=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...args){if(this.name==='state')throw new DOMException('injected write failure','QuotaExceededError');return orig.apply(this,args)};
    try{
     const b=Transactions.addCustomer({name:'عميل ب بعد الفشل'});out.bId=b.id;
     const s2=await DB.save(false);out.saveResult=s2;out.lastSaveError=DB.lastSaveError||'';
     out.reportedSuccess=!!(s2.indexedDb||(!out.lastSaveError));
     let rejected=false;try{await DB.atomicAsync('idb-fail-async',()=>Transactions.addCustomer({name:'عميل ج غير محفوظ'}))}catch(e){rejected=true}
     out.asyncRejected=rejected;out.asyncRolledBack=!DB.data.customers.some(x=>x.name==='عميل ج غير محفوظ');
    }finally{IDBObjectStore.prototype.put=orig}
    return out}''')
   await page.reload(wait_until='domcontentloaded');await page.wait_for_function('typeof DB!=="undefined" && DB.data')
   after=await page.evaluate('''async ids=>{const s=await DataStore.localGet();return {idbHasA:s.customers.some(x=>x.id===ids.aId),idbHasB:s.customers.some(x=>x.id===ids.bId),liveHasA:DB.data.customers.some(x=>x.id===ids.aId),liveHasB:DB.data.customers.some(x=>x.id===ids.bId)}}''',r)
   await browser.close()
  print(json.dumps({'injected':r,'afterReload':after},ensure_ascii=False,indent=1))
  assert r['saveResult'].get('indexedDb') is False,'save result must report IndexedDB failure: %r'%r['saveResult']
  assert r['asyncRejected'] and r['asyncRolledBack'],'awaited operation must reject and roll back memory on IndexedDB failure'
  assert r['lastSaveError'],'failed write must set an error (no silent success)'
  assert after['idbHasA'] and after['liveHasA'],'last good state lost after reload'
  assert not after['idbHasB'] and not after['liveHasB'],'unsaved change resurrected after reload'
  print('PASS case 8 (real IndexedDB)')
 finally: server.shutdown()
asyncio.run(main())
