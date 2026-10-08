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
 page.wait_for_function('!document.getElementById("modal").classList.contains("show") && document.getElementById("modalForm").dataset.submitting!=="1"')
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
  results.append({'id':label,'status':'FAIL','error':str(e),'uiDiagnostics':page.evaluate('()=>({page:UI.current,modal:document.getElementById("modal").className,pending:DB.pendingSaves,lastSaveError:DB.lastSaveError,revision:DB.saveRevision,journals:DB.data.journals.length,transfers:DB.data.transfers.length})'),'trace':traceback.format_exc()[-1500:],'body':page.locator('body').inner_text()[-2500:],'auth':page.evaluate('()=>({user:Auth.user,save:DB.lastSaveError,setup:DB.data.meta.setupComplete})')});print(label,'FAIL',str(e),flush=True)
 (OUT/'storage-ui-results.json').write_text(json.dumps({'results':results,'pageErrors':errors},ensure_ascii=False,indent=2))
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

import tempfile
with sync_playwright() as p:
 profile=tempfile.mkdtemp(prefix='elhafez-save-')
 def launch():
  return p.chromium.launch_persistent_context(profile,executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,service_workers='block',args=['--no-sandbox','--disable-dev-shm-usage'])
 context=launch();page=context.new_page();page.set_default_timeout(20000);page.on('dialog',lambda d:d.accept('QA'))
 seed(page);q=page.evaluate('()=>({a:DB.data.treasuries.find(x=>x.name==="QA Funded").id,b:DB.data.treasuries.find(x=>x.name==="QA Empty").id})')
 initial=raw(page);events=[]
 try:
  for n in range(1,271):
   tr=transfer(page,q['a'],q['b'],str(D('1.01')+(D(n%7)/100)))
   reverse_transfer(page,tr['id']);settled(page)
   event=page.evaluate('()=>({revision:DB.saveRevision,pending:DB.pendingSaves,error:DB.lastSaveError,save:DB.saveEvents.slice(-1),write:DataStore.writeEvents?.slice(-1)})')
   check(event['pending']==0 and not event['error'],'acknowledged but pending/error');check(event['save'][0]['status']=='commit','save commit')
   events.append({'cycle':n,**event})
   if n%10==0:print('UI cycles',n,flush=True);(OUT/'storage-commit-events.json').write_text(json.dumps(events,indent=2))
   if n%50==0 or n==270:
    before=raw(page);audit(before)
    disk=page.evaluate('async()=>await DataStore.localGet()')
    check(disk['transfers']==before['transfers'] and disk['journals']==before['journals'],'disk comparison')
    for j in before['journals']:
     check(abs(sum((D(str(l.get('baseDebit',0)))-D(str(l.get('baseCredit',0))) for l in j['lines']),D(0)))<D('.001'),'journal balance')
    context.close();context=launch();page=context.new_page();page.set_default_timeout(20000);page.on('dialog',lambda d:d.accept('QA'));page.goto(URL);page.wait_for_function('DB.data&&DB.data.meta.setupComplete')
    after=raw(page);(OUT/'storage-reopen-diff.json').write_text(json.dumps({'before':before['journals'],'after':after['journals']},ensure_ascii=False));check(sorted(after['journals'],key=lambda x:x['id'])==sorted(before['journals'],key=lambda x:x['id']),'journal identifiers preserved after actual close');check(after['transfers']==before['transfers'],'transfer identifiers preserved after actual close')
    page.locator('#loginForm [name=username]').wait_for(state='visible');page.locator('#loginForm [name=username]').fill('qa');page.locator('#loginForm [name=password]').fill('QATest123!');page.locator('#loginForm button[type=submit]').click(no_wait_after=True);page.wait_for_function('Auth.user?.username==="qa"&&!document.getElementById("app").classList.contains("hidden")')
    print('checkpoint',n,'journals',len(after['journals']),'transfers',len(after['transfers']),flush=True)
  result={'id':'F15-01','status':'PASS_STRESS_NOT_HISTORICAL_ROOT_CAUSE','cycles':270,'financialActions':540,'checkpoints':[50,100,150,200,250,270],'actualContextClose':True,'commitEvents':len(events),'independentBalancedJournals':len(raw(page)['journals']),'originalIncidentReproduced':False}
  (OUT/'storage-ui-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(OUT/'storage-commit-events.json').write_text(json.dumps(events,indent=2))
 except Exception as e:
  (OUT/'storage-ui-results.json').write_text(json.dumps({'id':'F15-01','status':'FAIL','cyclesCompleted':len(events),'error':str(e),'uiDiagnostics':page.evaluate('()=>({page:UI.current,modal:document.getElementById("modal").className,pending:DB.pendingSaves,lastSaveError:DB.lastSaveError,revision:DB.saveRevision,journals:DB.data.journals.length,transfers:DB.data.transfers.length})'),'trace':traceback.format_exc()},ensure_ascii=False,indent=2));raise
 finally:
  context.close();server.shutdown()
