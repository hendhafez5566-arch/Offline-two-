"""Acceptance on real Chromium IndexedDB; no storage mocks for the successful paths."""
import asyncio,json,os,pathlib,threading,http.server,functools
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
async def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox','--disable-dev-shm-usage'])
   page=await browser.new_page()
   await page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded')
   await page.wait_for_function('typeof DB!=="undefined" && DB.data')
   result=await page.evaluate('''async()=>{
    const check=(v,m)=>{if(!v)throw Error(m)};
    ServerStore.available=false;ServerStore.authenticated=false;
    DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();
    const u={id:'qa-admin',name:'QA',role:'admin',active:true,permissions:{all:true},allowedBranchIds:[]};DB.data.users=[u];Auth.user=u;
    const customer=Transactions.addCustomer({name:'عميل حفظ حقيقي'});
    const inv=Invoices.create({kind:'customer',partyId:customer.id,partyType:'customer',currency:'EGP',date:'2026-10-06',lines:[{description:'خدمة',qty:1,price:123.45,taxId:'VAT14',accountId:'4200'}],status:'draft'});Invoices.post(inv);
    const file=new File(['original attachment'],'original.txt',{type:'text/plain'}),a=await Attachments.add({entityType:'customer',entityId:customer.id},file);
    check(await DataStore.localPut(DB.data),'state write');
    const saved=await DataStore.localGet();check(saved.invoices.some(x=>x.id===inv.id),'invoice persisted');
    const pkg=await Backup.build();check(pkg.attachments.length===1,'backup file missing');
    const previous=JSON.stringify(DB.data),replacement=deep(pkg);replacement.data.company.name='replacement';replacement.checksum=await Backup.checksum(JSON.stringify({data:replacement.data,attachments:replacement.attachments,blobs:replacement.blobs}));
    const original=AttachmentStore.localPut;let fail=true;AttachmentStore.localPut=async(...args)=>{if(fail){fail=false;return false}return original.apply(AttachmentStore,args)};
    let rejected=false;try{await Backup.restorePackage(replacement)}catch(e){rejected=true}finally{AttachmentStore.localPut=original}
    check(rejected,'failed restore succeeded');check(JSON.stringify(DB.data)===previous,'memory rollback');
    check(JSON.stringify(await DataStore.localGet())===previous,'durable rollback');check(await(await AttachmentStore.get(a.id)).text()==='original attachment','file rollback');
    return {invoiceId:inv.id,attachmentId:a.id,stateSaved:true,restoreFailureRejected:true,memoryRollback:true,indexedDbRollback:true,fileRollback:true};
   }''')
   await page.reload(wait_until='domcontentloaded');await page.wait_for_function('typeof DB!=="undefined" && DB.data')
   persisted=await page.evaluate('''async ids=>{const s=await DataStore.localGet(),f=await AttachmentStore.get(ids.attachmentId);return {invoice:s.invoices.some(x=>x.id===ids.invoiceId),attachment:!!f&&await f.text()==='original attachment'}}''',result)
   assert persisted['invoice'] and persisted['attachment'],persisted
   print(json.dumps({'ok':True,**result,'afterReload':persisted},ensure_ascii=False,indent=2))
   await browser.close()
 finally:server.shutdown()
asyncio.run(main())
