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
 if os.environ.get('FOCUS') and label not in os.environ['FOCUS'].split(','):return
 try:
  facts=fn();results.append({'id':label,'status':'PASS','facts':facts});print(label,'PASS',flush=True)
 except Exception as e:
  results.append({'id':label,'status':'FAIL','error':str(e),'trace':traceback.format_exc()[-1500:],'body':page.locator('body').inner_text()[-2500:],'auth':page.evaluate('()=>({user:Auth.user,save:DB.lastSaveError,setup:DB.data.meta.setupComplete})')});print(label,'FAIL',str(e),flush=True)
 (OUT/'ui-results.json').write_text(json.dumps({'results':results,'pageErrors':errors},ensure_ascii=False,indent=2))
def seed(page):
 page.goto(URL,wait_until='domcontentloaded');page.wait_for_function('typeof DB!=="undefined"&&DB.data');page.wait_for_timeout(300)
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
 context=browser.new_context(accept_downloads=True,service_workers='block');page=context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept('QA reversal'))
 seed(page)
 def lines():
  customer=add_invoice(page,'customer',[100,200,300]);supplier=add_invoice(page,'supplier',[200,300,400],'QA-3-LINES')
  d=raw(page);audit(d);check(len(customer['lines'])==3 and len(supplier['lines'])==3,'three lines')
  check(balance(d,'1200',page.evaluate('DB.data.customers.find(x=>x.name==="QA Customer").id'))==600,'customer ledger 600');check(balance(d,'2100',page.evaluate('DB.data.suppliers.find(x=>x.name==="QA Supplier").id'))==-900,'supplier ledger 900')
  page.reload();page.wait_for_function('DB.data&&DB.data.invoices.length===2')
  check([len(i['lines']) for i in raw(page)['invoices']]==[3,3],'persisted lines')
  return {'customer':customer['no'],'supplier':supplier['no'],'rawTotals':[600,900],'reloaded':True}
 scene('F11-01',lines)
 def permissions():
  login(page,'salesqa');nav(page,'invoices');check(page.locator('[data-clean-kind=supplier]:visible').count()==0,'no purchase tab')
  page.locator('#globalSearch').fill('QA-3-LINES');page.wait_for_timeout(180);check('QA-3-LINES' not in page.locator('#searchResults').inner_text(),'search leak')
  blocked=page.evaluate("""()=>{const i=DB.data.invoices.find(x=>x.kind==='supplier');try{Print.invoice(i.id);return false}catch(e){return e.message.includes('مسموح')}}""");check(blocked,'direct print guard')
  login(page,'qa');nav(page,'invoices');page.locator('[data-clean-kind=supplier][data-clean-action=setInvoiceKind]').click(no_wait_after=True);reveal_click(page,'[data-print-invoice]');check('900' in page.locator('#printBody').inner_text() or '٩٠٠' in page.locator('#printBody').inner_text(),'admin print');page.evaluate('Print.close()')
  return {'actualSalesLogin':True,'listAndSearchBlocked':True,'directPrintBlocked':True,'adminPrint':True}
 scene('F11-02',permissions)
 def negative():
  login(page,'qa');q=page.evaluate('()=>({c:DB.data.customers.find(x=>x.name==="QA Customer").id,s:DB.data.suppliers.find(x=>x.name==="QA Supplier").id,a:DB.data.treasuries.find(x=>x.name==="QA Funded").id,b:DB.data.treasuries.find(x=>x.name==="QA Empty").id,bank:DB.data.treasuries.find(x=>x.name==="QA Bank").id})');t1=transfer(page,q['a'],q['b'],100);t2=transfer(page,q['b'],q['bank'],100);before=raw(page);reverse_transfer(page,t1['id']);after=raw(page)
  check(len(before['journals'])==len(after['journals']),'rejected reversal journals unchanged');check(after['transfers'][1]['status']=='posted','first remains posted')
  close(page);reverse_transfer(page,t2['id']);settled(page);reverse_transfer(page,t1['id']);settled(page);d=raw(page);audit(d)
  aid=next(l['accountId'] for j in d['journals'] for l in j['lines'] if l.get('treasuryId')==q['b']);check(balance(d,aid,native=True)==0,'empty treasury returns zero')
  page.reload();page.wait_for_function('DB.data');check(raw(page)['transfers'][1]['status']=='void','reopened reversal')
  return {'rejectWithoutMutation':True,'dependentThenOriginalReversed':True,'emptyNativeBalance':0,'reloaded':True}
 scene('F15-02',negative)
 def advance():
  login(page,'qa');nav(page,'customers');page.locator('[data-form-open=customer]:visible').first.click(no_wait_after=True);page.locator('#modalBody [name=name]').fill('QA Advance Customer');submit(page);settled(page);r=receipt(page,120000,party='QA Advance Customer');inv=add_invoice(page,'customer',[395000],party='QA Advance Customer');receipt(page,275000,inv['id'],party='QA Advance Customer')
  nav(page,'invoices');page.locator('[data-clean-kind=customer][data-clean-action=setInvoiceKind]').click(no_wait_after=True)
  reveal_click(page,f'[data-clean-action=applyAdvance][data-clean-id="{inv["id"]}"]');page.locator('#modalBody [name=amount]').fill('120000')
  before=raw(page);submit(page);settled(page);d=raw(page);audit(d);check(len(d['receipts'])==len(before['receipts']),'no new receipt');check(len(d['journals'])==len(before['journals'])+1,'one settlement journal')
  st=d['customerSettlements'][0];check(st['invoiceAllocations'][0]['invoiceAmount']==120000,'allocation');check(balance(d,'2400',page.evaluate('DB.data.customers.find(x=>x.name==="QA Advance Customer").id'))==0,'advance zero')
  page.reload();page.wait_for_function('DB.data');check(raw(page)['customerSettlements'][0]['id']==st['id'],'settlement persisted')
  return {'settlement':st['no'],'applied':120000,'newCashMovements':0,'reloaded':True}
 scene('F11-03',advance)
 (OUT/'raw-final.json').write_text(json.dumps(raw(page),ensure_ascii=False))
 browser.close();server.shutdown()
 check(all(x['status']=='PASS' for x in results),'UI acceptance failures')
