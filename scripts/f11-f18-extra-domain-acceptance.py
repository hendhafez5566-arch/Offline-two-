"""Directed domain regressions in real Chromium and IndexedDB. Does not claim UI acceptance."""
import functools,http.server,threading,pathlib,os,json,traceback
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/repairs-f11-f18';OUT.mkdir(parents=True,exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Q,directory=str(ROOT/'dist')));threading.Thread(target=s.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=b.new_page()
 baseline=os.environ.get('BASELINE_APP')
 if baseline:page.route('**/app.js*',lambda route:route.fulfill(path=baseline,content_type='application/javascript'))
 page.goto(f'http://127.0.0.1:{s.server_port}/');page.wait_for_function('typeof DB!=="undefined"&&DB.data')
 result=page.evaluate("""async()=>{
 await DB.save(false);ServerStore.available=false;
 const results=[],assert=(v,l)=>{if(!v)throw Error(l)},near=(a,b,l)=>assert(Math.abs(a-b)<.000001,l+': '+a+' != '+b);
 const reset=()=>{DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();UmrahCore_DB.load();const u={id:'qa',name:'QA',role:'admin',permissions:{all:true},active:true,approvalLimit:1e12};DB.data.users=[u];Auth.user=u;Accounting.invalidateLineCache()};
 const test=async(id,work)=>{await DB.saveQueue;reset();try{const facts=await work();await DB.save(false);const disk=await DataStore.localGet();assert(JSON.stringify(disk.journals)===JSON.stringify(DB.data.journals),'raw journal disk equality');results.push({id,status:'PASS',facts})}catch(e){results.push({id,status:'FAIL',error:e.message})}};
 const date=today(),treasury=(currency='EGP',amount=500000)=>Transactions.createTreasury({name:'QA '+currency,currency,type:'cash',opening:amount,date,silent:true});
 const invoice=(kind,amount,currency='EGP')=>{const party=kind==='supplier'?Transactions.addSupplier({name:'QA supplier',currency}):Transactions.addCustomer({name:'QA customer'}),inv=Invoices.create({kind,partyId:party.id,partyType:kind==='supplier'?'supplier':'customer',currency,date,lines:[{description:'QA',qty:1,price:amount,taxId:'TAX0',accountId:kind==='supplier'?'5100':'4200'}],status:'draft'});Invoices.post(inv);return {party,inv}};
 await test('F11-03-extra',()=>{const c=Transactions.addCustomer({name:'QA advance'}),cash=treasury();const r=Transactions.addReceipt({partyType:'customer',partyId:c.id,treasuryId:cash.id,amount:120000,currency:'EGP',date});const inv=Invoices.create({kind:'customer',partyId:c.id,partyType:'customer',currency:'EGP',date,lines:[{description:'QA',qty:1,price:395000,taxId:'TAX0',accountId:'4200'}],status:'draft'});Invoices.post(inv);Transactions.addReceipt({partyType:'customer',partyId:c.id,treasuryId:cash.id,amount:275000,currency:'EGP',invoiceId:inv.id,date});
 const apply=()=>AdvancedAccounting.applyCustomerAdvance({invoiceId:inv.id,amount:120000,date,reason:'QA'});const a=apply();let blocked=false;try{Transactions.voidReceipt(r.id,'QA')}catch(e){blocked=true}assert(blocked,'consumed receipt reversal blocked');let duplicate=false;try{apply()}catch(e){duplicate=true}assert(duplicate,'second application blocked');AdvancedAccounting.reverseSettlement('customer',a.id,'QA');near(Accounting.customerAdvance('customer',c.id).EGP,120000,'advance released');const b=apply();assert(b.id!==a.id,'reapply distinct record');near(Accounting.customerAdvance('customer',c.id).EGP,0,'advance zero');return {consumedReceiptBlocked:true,duplicateBlocked:true,reverseAndReapply:true,noNewCash:true}});
 await test('F16-01-ambiguity',()=>{const t=Transactions.createTreasury({name:'QA bank',currency:'EGP',type:'bank',opening:100000,date,silent:true}),j=DB.data.journals.length;DB.data.bankStatementLines.push({id:'bank-a',treasuryId:t.id,date,amount:100000,currency:'EGP',status:'unmatched',reference:''},{id:'bank-b',treasuryId:t.id,date,amount:100000,currency:'EGP',status:'unmatched',reference:''});const r=AdvancedAccounting.reconcileBankLines(t.id);assert(DB.data.bankMatches.length===0,'ambiguous duplicate not selected');assert(DB.data.journals.length===j,'no ledger changed');return {ambiguousBothPending:true,newJournals:0}});
 return results;
 }""")
 (OUT/'extra-domain-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));b.close();s.shutdown()
 if any(x['status']!='PASS' for x in result):raise SystemExit(1)
