"""Durability regressions on real Chromium: failure, fallback, abort and quota."""
import asyncio, functools, http.server, json, os, pathlib, threading
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

async def ready(page, url):
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_function('typeof DB !== "undefined" && DB.data')
    # Let deferred boot persistence finish before injecting faults.
    await page.wait_for_timeout(500)

async def main():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT/'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'), headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = await browser.new_page()
            await ready(page, url)
            result = await page.evaluate('''async () => {
                const check=(ok,msg)=>{if(!ok)throw Error(msg)};
                ServerStore.available=false;ServerStore.authenticated=false;
                DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();
                const u={id:'qa-admin',name:'QA',role:'admin',active:true,permissions:{all:true},allowedBranchIds:[]};
                DB.data.users=[u];Auth.user=u;
                await DB.atomicAsync('good',()=>Transactions.addCustomer({name:'Durable A'}));
                const before=JSON.stringify(DB.data),cacheBefore=localStorage.getItem(APP.storage);
                const originalPut=IDBObjectStore.prototype.put;
                IDBObjectStore.prototype.put=function(...args){if(this.name==='state')throw new DOMException('injected quota','QuotaExceededError');return originalPut.apply(this,args)};
                try {
                    let rejected=false;
                    try {await DB.atomicAsync('rejected B',()=>Transactions.addCustomer({name:'Rejected B'}));} catch(e) {rejected=true;}
                    check(rejected,'async write must reject');
                    check(JSON.stringify(DB.data)===before,'memory must exactly roll back');
                    check(localStorage.getItem(APP.storage)===cacheBefore,'fallback must not contain rejected B');
                    check(JSON.stringify(await DataStore.localGet())===before,'IndexedDB must retain A');
                    Transactions.addCustomer({name:'Unsaved sync C'});
                    const failed=await DB.save(false);
                    check(failed.durable===false && !!DB.lastSaveError,'sync save must report non-durable');
                    check(localStorage.getItem(APP.storage)===cacheBefore,'fallback must not contain unsaved C');
                } finally {IDBObjectStore.prototype.put=originalPut;DB.installRestoredState(JSON.parse(before));}
                // Abort an actual transaction; suppress request error bubbling to exercise onabort itself.
                IDBObjectStore.prototype.put=function(...args){
                    const req=originalPut.apply(this,args);
                    if(this.name==='state'){req.addEventListener('error',e=>{e.preventDefault();e.stopPropagation()});this.transaction.abort();}
                    return req;
                };
                try {
                    const saved=await Promise.race([DB.save(false),new Promise((_,reject)=>setTimeout(()=>reject(Error('aborted transaction hung')),2000))]);
                    check(saved.durable===false,'abort must report failure');
                    check(localStorage.getItem(APP.storage)===cacheBefore,'abort must preserve fallback');
                } finally {IDBObjectStore.prototype.put=originalPut;DB.installRestoredState(JSON.parse(before));}
                // IndexedDB remains authoritative even if updating the redundant cache hits quota.
                const originalSet=Storage.prototype.setItem;
                Storage.prototype.setItem=function(k,v){if(this===localStorage&&k===APP.storage)throw new DOMException('cache quota','QuotaExceededError');return originalSet.call(this,k,v)};
                try {
                    const saved=await DB.save(false);
                    check(saved.indexedDb===true&&saved.cache===false&&saved.durable===true,'IDB success must tolerate cache quota');
                    check(!DB.lastSaveError,'successful IDB save must clear error');
                } finally {Storage.prototype.setItem=originalSet;}
                return {writeFailureRollback:true,syncFailurePreservesCache:true,transactionAbort:true,cacheQuotaWithIdbSuccess:true};
            }''')
            # A real read failure on reload must select the intact localStorage fallback.
            await page.add_init_script('''const get=IDBObjectStore.prototype.get;IDBObjectStore.prototype.get=function(...a){if(this.name==='state')throw new DOMException('injected read failure','UnknownError');return get.apply(this,a)};''')
            await ready(page, url)
            recovered = await page.evaluate('''()=>({a:DB.data.customers.some(x=>x.name==='Durable A'),b:DB.data.customers.some(x=>x.name==='Rejected B'),c:DB.data.customers.some(x=>x.name==='Unsaved sync C')})''')
            assert recovered == {'a':True,'b':False,'c':False}, recovered
            result['readFailureFallbackAfterReload'] = True
            await page.close()
            # A separate browser context has no IndexedDB access at all: localStorage is the sole durable store.
            context = await browser.new_context()
            await context.add_init_script("indexedDB.open=()=>{throw new DOMException('blocked IndexedDB','SecurityError')}")
            page = await context.new_page()
            await ready(page, url)
            fallback = await page.evaluate('''async()=>{
                const check=(ok,msg)=>{if(!ok)throw Error(msg)};
                ServerStore.available=false;ServerStore.authenticated=false;
                DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();
                const u={id:'qa-admin',name:'QA',role:'admin',active:true,permissions:{all:true},allowedBranchIds:[]};DB.data.users=[u];Auth.user=u;
                await DB.atomicAsync('fallback good',()=>Transactions.addCustomer({name:'Fallback A'}));
                const saved=await DB.save(false);
                check(saved.durable===true&&saved.indexedDb===false&&saved.cache===true,'localStorage-only save must work');
                const before=JSON.stringify(DB.data),cache=localStorage.getItem(APP.storage),set=Storage.prototype.setItem;
                Storage.prototype.setItem=function(k,v){if(this===localStorage&&k===APP.storage)throw new DOMException('quota','QuotaExceededError');return set.call(this,k,v)};
                try {
                    let rejected=false;try{await DB.atomicAsync('both fail',()=>Transactions.addCustomer({name:'Rejected fallback B'}))}catch(e){rejected=true}
                    check(rejected&&JSON.stringify(DB.data)===before,'both unavailable must reject and roll back');
                    check(localStorage.getItem(APP.storage)===cache,'last fallback preserved');
                } finally {Storage.prototype.setItem=set;}
                return {localStorageOnlySave:true,bothStoresFailRollback:true};
            }''')
            await ready(page, url)
            assert await page.evaluate("DB.data.customers.some(x=>x.name==='Fallback A')&&!DB.data.customers.some(x=>x.name==='Rejected fallback B')"), 'fallback reload lost good state'
            result.update(fallback)
            result['localStorageOnlyReload'] = True
            await browser.close()
            print(json.dumps({'passed':len(result),'failed':0,'checks':result}, indent=2))
    finally:
        server.shutdown()

asyncio.run(main())
