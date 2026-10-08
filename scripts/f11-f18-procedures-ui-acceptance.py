"""Targeted real Chromium UI acceptance. Fixtures are explicit; mutations under test use forms/buttons.
No screenshots; raw journals independently checked with Decimal. Run with CHROMIUM_PATH.
"""
import os,json,threading,http.server,functools,pathlib,sys,traceback
from decimal import Decimal as D
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/repairs-f11-f18';OUT.mkdir(parents=True,exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')));threading.Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/'
results=[];errors=[]
def check(x,label):
 if not x:raise AssertionError(label)
def raw(page):return page.evaluate('()=>JSON.parse(JSON.stringify(DB.data))')
def balance(data,account,party='',currency='',native=False):
 out=D(0)
 for j in data['journals']:
  if j.get('status') in ('void','cancelled','draft'):continue
  for l in j['lines']:
   if l['accountId']!=account or (party and l.get('partyId')!=party) or (currency and l.get('currency')!=currency):continue
   if native and l.get('baseOnly'):continue
   out+=D(str(l.get('debit' if native else 'baseDebit',0)))-D(str(l.get('credit' if native else 'baseCredit',0)))
 return out
def audit(data):
 for j in data['journals']:
  check(abs(sum((D(str(l.get('baseDebit',0)))-D(str(l.get('baseCredit',0))) for l in j['lines']),D(0)))<D('.001'),j['no']+' unbalanced')
def nav(page,name):
 page.wait_for_function('!DB._renderScheduled');page.evaluate('(n)=>UI.openPage(n)',name)
def submit(page):
 page.locator('#modalForm button[type=submit]').click(no_wait_after=True)
 page.wait_for_timeout(120)
def close(page):page.evaluate('UI.closeModal(true)')
def reveal_click(page,selector):
 el=page.locator(selector).first
 ds=el.locator('xpath=ancestor::details')
 if ds.count() and ds.first.get_attribute('open') is None:ds.first.locator('summary').first.click(no_wait_after=True)
 el.click(no_wait_after=True)
def reason(page):
 page.locator('#modalBody [name=reason]').fill('QA acceptance reversal')
 submit(page)
def picker(page,name,label):
 w=page.locator('#modalBody .smart-picker').filter(has=page.locator(f'input[name="{name}"]')).first
 w.locator('.picker-input').fill(label)
 w.locator('.picker-option').first.click(no_wait_after=True)
def settled(page):page.wait_for_function('DB.pendingSaves===0 && !DB.lastSaveError')
def scene(label,fn):
 try:
  facts=fn();results.append({'id':label,'status':'PASS','facts':facts});print(label,'PASS',flush=True)
 except Exception as e:
  results.append({'id':label,'status':'FAIL','error':str(e),'trace':traceback.format_exc()[-1500:],'body':page.locator('body').inner_text()[-2500:],'auth':page.evaluate('()=>({user:Auth.user,save:DB.lastSaveError,setup:DB.data.meta.setupComplete})')});print(label,'FAIL',str(e),flush=True)
 (OUT/'procedures-ui-results.json').write_text(json.dumps({'results':results,'pageErrors':errors},ensure_ascii=False,indent=2))
def seed(page):
 page.goto(URL,wait_until='domcontentloaded');page.wait_for_function('typeof DB!=="undefined"&&DB.data');page.wait_for_function('document.querySelector("#setupPanel:not(.hidden),#loginForm:not(.hidden),#app:not(.hidden)")');page.wait_for_timeout(300)
 page.evaluate("""async()=>{
 await DB.saveQueue;
 DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();UmrahCore_DB.load();
 const u={id:'qa-admin',name:'QA Admin',username:'qa',role:'admin',active:true,onboardingSeen:true,permissions:{all:true},approvalLimit:1e12};await Security.setPassword(u,'QATest123!');DB.data.users=[u];Auth.user=u;
 const sales={id:'qa-sales',name:'QA Sales',username:'salesqa',role:'sales',viewCosts:false,active:true,onboardingSeen:true,permissions:deep(RolePermissions.sales),branchId:DB.data.branches[0]?.id,allowedBranchIds:DB.data.branches.map(x=>x.id)};await Security.setPassword(sales,'QATest123!');DB.data.users.push(sales);
 const c=Transactions.addCustomer({name:'QA Customer',type:'company'}),s=Transactions.addSupplier({name:'QA Supplier',currency:'EGP'});
 const a=Transactions.createTreasury({name:'QA Funded',currency:'EGP',type:'cash',opening:500000,date:today(),silent:true}),b=Transactions.createTreasury({name:'QA Empty',currency:'EGP',type:'cash',opening:0,date:today(),silent:true}),bank=Transactions.createTreasury({name:'QA Bank',currency:'EGP',type:'bank',opening:100000,date:today(),silent:true});
 await Commercial.afterInit();Object.assign(DB.data.users.find(u=>u.id==='qa-sales'),{branchId:DB.data.branches[0]?.id,allowedBranchIds:DB.data.branches.map(x=>x.id)});window.qa={c:c.id,s:s.id,a:a.id,b:b.id,bank:bank.id};await DB.save(false);Auth.enter();UI.openPage('invoices');
 }""")
 settled(page)
def login(page,user='qa'):
 page.evaluate('Auth.logout()')
 page.locator('#loginForm [name=username]').wait_for(state='visible');page.wait_for_function('DB.data&&DB.data.users.length>0');page.locator('#loginForm [name=username]').fill(user);page.locator('#loginForm [name=password]').fill('QATest123!')
 page.locator('#loginForm button[type=submit]').click(no_wait_after=True);page.wait_for_function('(u)=>Auth.user?.username===u && !document.getElementById("app").classList.contains("hidden")',arg=user)
def add_invoice(page,kind,prices,external='',currency='EGP',party='QA Customer'):
 nav(page,'invoices');page.locator(f'[data-clean-action=setInvoiceKind][data-clean-kind={kind}]').click(no_wait_after=True)
 page.locator('[data-clean-action=newInvoice]').click(no_wait_after=True);picker(page,'party','QA Supplier' if kind=='supplier' else party)
 page.locator('#modalBody [name=currency]').select_option(currency)
 if external:page.locator('#modalBody [name=externalNo]').fill(external)
 for i,price in enumerate(prices):
  if i:page.locator('[data-form-add-line=invoice]').click(no_wait_after=True)
  page.locator('[name=lineDesc]').nth(i).fill('QA line '+str(i+1));page.locator('[name=linePrice]').nth(i).fill(str(price));page.locator('[name=lineAccount]').nth(i).select_option('5100' if kind=='supplier' else '4200')
 page.locator('[data-value=posted]').click(no_wait_after=True);submit(page);settled(page)
 return raw(page)['invoices'][0]
def transfer(page,a,b,amount,received=None):
 nav(page,'treasury');page.locator('[data-treasury-tab=transfers]').click(no_wait_after=True);page.locator('[data-form-open=transfer]').click(no_wait_after=True)
 page.locator('#modalBody [name=from]').select_option(a);page.locator('#modalBody [name=to]').select_option(b);page.locator('#modalBody [name=amount]').fill(str(amount))
 if received is not None:page.locator('#modalBody [name=received]').fill(str(received))
 submit(page);settled(page);return raw(page)['transfers'][0]
def reverse_transfer(page,id):
 nav(page,'treasury');page.locator('[data-treasury-tab=transfers]').click(no_wait_after=True);reveal_click(page,f'[data-clean-action=reverseTransfer][data-clean-id="{id}"]');reason(page)
def receipt(page,amount,invoice=None,party='QA Customer'):
 nav(page,'receipts');page.locator('[data-clean-action=newVoucher]').click(no_wait_after=True);picker(page,'partyRef',party)
 page.locator('#modalBody [name=amount]').fill(str(amount));page.locator('#modalBody [name=treasuryId]').select_option(page.evaluate('DB.data.treasuries.find(x=>x.name==="QA Funded").id'))
 if invoice:page.locator('#modalBody [name=invoiceId]').select_option(invoice)
 submit(page);settled(page);return raw(page)['receipts'][0]

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 context=browser.new_context(accept_downloads=True,service_workers='block');page=context.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept('QA'))
 seed(page)
 def bank():
  nav(page,'treasury');page.locator('[data-treasury-tab=bank]').click(no_wait_after=True);page.locator('[data-form-open=bankStatement]').click(no_wait_after=True)
  page.locator('#modalBody [name=treasuryId]').select_option(page.evaluate('DB.data.treasuries.find(t=>t.name==="QA Bank").id'));page.locator('#modalBody [name=linesText]').fill(chr(10).join(['2026-10-08,100000,QA-OPEN,Opening','2026-10-08,777,QA-NONE,No ledger']));submit(page);settled(page)
  nav(page,'treasury');page.locator('[data-treasury-tab=bank]').click(no_wait_after=True);before=raw(page);page.locator('[data-advanced-action=reconcileImportedBank]').click(no_wait_after=True);settled(page);after=raw(page)
  check(len(after['bankMatches'])==1,'one unique match');check(len(after['journals'])==len(before['journals']),'no accounting movement');check([x['status'] for x in after['bankStatementLines']]==['matched','unmatched'],'statuses')
  page.locator('[data-advanced-action=reconcileImportedBank]').click(no_wait_after=True);settled(page);check(len(raw(page)['bankMatches'])==1,'idempotent')
  page.reload();page.wait_for_function('DB.data');check(len(raw(page)['bankMatches'])==1,'saved matches')
  return {'uniqueMatched':1,'unmatched':1,'newJournals':0,'repeatAndReload':True}
 scene('F16-01',bank)
 def rebill():
  login(page);f=page.evaluate("""async()=>{const po=CRM.addPO({supplierId:DB.data.suppliers[0].id,currency:'EGP',date:today(),lines:[{description:'QA units',qty:2,price:200,taxId:'TAX0'}]});CRM.approvePO(po.id);await DB.save(false);return {id:po.id,line:po.lines[0].id}}""")
  ids=[]
  for n in [1,2]:
   nav(page,'purchaseorders');reveal_click(page,f'[data-clean-action=receivePO][data-clean-id="{f["id"]}"]');page.locator(f'#modalBody [name="qty_{f["line"]}"]').fill(str(n));submit(page);settled(page)
   nav(page,'purchaseorders');reveal_click(page,f'[data-clean-action=convertPO][data-clean-id="{f["id"]}"]');settled(page);ids.append(raw(page)['invoices'][0]['id'])
  nav(page,'invoices');page.locator('[data-clean-action=setInvoiceKind][data-clean-kind=supplier]').click(no_wait_after=True);reveal_click(page,f'[data-clean-action=cancelInvoice][data-clean-id="{ids[0]}"]');reason(page);settled(page)
  page.reload();page.wait_for_function('DB.data');login(page);nav(page,'purchaseorders');reveal_click(page,f'[data-clean-action=convertPO][data-clean-id="{f["id"]}"]');settled(page)
  d=raw(page);audit(d);invoices=[i for i in d['invoices'] if i.get('sourceId')==f['id']];check(len(invoices)==3,'replacement exists');check(len(set(i['externalNo'] for i in invoices))==3,'unique references');check(balance(d,'5100')==400,'net cost 400');check(balance(d,'2100')==-400,'payable 400')
  page.reload();page.wait_for_function('DB.data');check(len([i for i in raw(page)['invoices'] if i.get('sourceId')==f['id']])==3,'saved replacement')
  return {'newReference':invoices[0]['externalNo'],'netCost':400,'payable':400,'reloadRetry':True}
 scene('F18-01',rebill)
 def backup():
  login(page);nav(page,'documents');page.locator('[data-form-open=attachment]:visible').first.click(no_wait_after=True);page.locator('#modalBody [name=entityId]').fill(page.evaluate('DB.data.customers[0].no'));page.locator('#modalBody [name=file]').set_input_files({'name':'qa-attachment.txt','mimeType':'text/plain','buffer':b'QA durable attachment 2026-10-08'});submit(page);settled(page)
  a=raw(page)['attachments'][0];diag=page.evaluate('async(id)=>({meta:DB.data.attachments.find(x=>x.id===id),blobSize:(await AttachmentStore.get(id))?.size,db:APP.filesDb})',a['id']);check(diag['blobSize']==len(b'QA durable attachment 2026-10-08'),'stored blob size')
  nav(page,'backup-center')
  with page.expect_download() as download:
   page.locator('[data-commercial-action=externalBackup][data-commercial-mode=download]').click(no_wait_after=True)
  file=download.value.path();pkg=json.loads(pathlib.Path(file).read_text());check(len(pkg['attachments'])==1 and len(pkg['blobs'])==1,'complete backup contains bytes')
  before=raw(page);nav(page,'customers');page.locator('[data-form-open=customer]:visible').first.click(no_wait_after=True);page.locator('#modalBody [name=name]').fill('QA post-backup extra');submit(page);settled(page)
  nav(page,'backup-center');page.locator('#backupRestoreFile').set_input_files(file);page.locator('#restoreSafetyBackup').wait_for();# retain safety backup default
  submit(page);page.wait_for_timeout(1000);page.wait_for_function('DB.data&&DB.data.meta.restoredFrom==="backup"')
  after=raw(page);check(not any(c['name']=='QA post-backup extra' for c in after['customers']),'actual restore removes later record');check(after['journals']==before['journals'],'raw ledger restored');check(page.evaluate('async(id)=>(await AttachmentStore.get(id)).text()',a['id'])=='QA durable attachment 2026-10-08','attachment restored bytes')
  return {'healthyMetadataAndBlob':True,'backupContainsBytes':True,'restoreActuallyExecuted':True,'rawLedgerEqual':True,'attachmentBytesRestored':True,'historicalMissingCause':'not available without original company profile'}
 scene('F17',backup)
 browser.close();server.shutdown()
 check(all(x['status']=='PASS' for x in results),'procedures UI failures')
