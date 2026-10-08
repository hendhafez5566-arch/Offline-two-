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
 (OUT/'wizard-ui-acceptance-results.json').write_text(json.dumps({'results':results,'pageErrors':errors},ensure_ascii=False,indent=2))
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
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage']);page=browser.new_page();page.set_default_timeout(15000);page.on('dialog',lambda d:d.accept('QA'))
 seed(page)
 def wizard():
  page.evaluate("""()=>{const date='2026-11-10',back='2026-11-15',token='QA-LABEL',name='QA planning label';UmrahCore_ProgramWizard.data={...UmrahCore_ProgramWizard.defaults(),creationToken:token,programType:'umrah',name,groupNo:'E2E-01',departureDate:date,returnDate:back,capacity:10,currency:'EGP',fxRate:1,defaultTreasuryId:DB.data.treasuries.find(t=>t.name==="QA Funded").id,holdHours:24,depositMin:0,stay1Source:'direct',stay1ContractId:'',stay1City:'Makkah',stay1Label:'مكة',stay1Hotel:'فندق دورة كاملة',stay1SupplierId:DB.data.suppliers[0].id,stay1Currency:'EGP',stay1FxRate:1,stay1Nights:5,stay1SingleQty:0,stay1SingleRate:0,stay1DoubleQty:5,stay1DoubleRate:100,stay1TripleQty:0,stay1TripleRate:0,stay1QuadQty:0,stay1QuadRate:0,stay1QuintQty:0,stay1QuintRate:0,stay2Hotel:'',stay2Nights:0,stay3Hotel:'',stay3Nights:0,flightSource:'direct',flightContractId:'',airline:'Test Air',flightSupplierId:DB.data.suppliers[0].id,flightCurrency:'EGP',flightFxRate:1,outFlight:'TA100',outFrom:'CAI',outTo:'JED',outDateTime:date+'T06:00',returnFlight:'TA101',returnFrom:'JED',returnTo:'CAI',returnDateTime:back+'T18:00',seats:10,costPerSeat:1000,flightPolicy:'block',transportProvider:'',transportCost:0,visaSupplierId:'',visaCost:0,priceDouble:5000,priceSingle:0,priceTriple:0,priceQuad:0,priceQuint:0,childBed:0,childNoBed:0,infant:0,profitMode:'percent',marginPct:15,allowLossPricing:'no'};UmrahCore_ProgramWizard.step=6;UmrahCore_ProgramWizard.maxStep=6;UmrahCore_UI.openPage('guided-program')}""")
  b=page.locator('[data-pw-finish]');check(b.inner_text()=='حفظ البرنامج للتخطيط والمراجعة','accurate button label');b.click(no_wait_after=True);settled(page)
  page.wait_for_function('DB.data.umrahPrograms.some(x=>x.creationToken==="QA-LABEL")');d=raw(page);pr=next(x for x in d['umrahPrograms'] if x.get('creationToken')=='QA-LABEL');check(pr['status']=='planning','planning status');check(not page.evaluate('(id)=>UmrahCore_Forms.pickerSource("saleProgram").some(x=>x.value===id)',pr['id']),'not for sale')
  page.reload();page.wait_for_function('DB.data&&DB.data.umrahPrograms');check(next(x for x in raw(page)['umrahPrograms'] if x['id']==pr['id'])['status']=='planning','planning saved');return {'labelCorrect':True,'actualSavePlanning':True,'notForSale':True,'reloaded':True}
 scene('F12-01',wizard)
 (OUT/'wizard-ui-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));browser.close();server.shutdown();check(all(x['status']=='PASS' for x in results),'wizard UI failure')
