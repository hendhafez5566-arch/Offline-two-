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
 await test('F15-02-multicurrency',()=>{Currency.setRate('SAR',10,date);const a=treasury('EGP',1000),b=treasury('SAR',0),c=treasury('SAR',0);const one=Transactions.transfer({from:a.id,to:b.id,amount:100,received:10,date});const onward=Transactions.transfer({from:b.id,to:c.id,amount:5,date});const count=DB.data.journals.length;let blocked=false;try{Transactions.reverseTransfer(one.id,'QA')}catch(e){blocked=true}assert(blocked,'partial SAR balance blocks reversal');assert(DB.data.journals.length===count&&one.status==='posted','rejected unchanged');Transactions.reverseTransfer(onward.id,'QA');Transactions.reverseTransfer(one.id,'QA');return {partialNativeBalance:5,neededNative:10,rejectedWithoutMutation:true,dependentThenOriginal:true}});
 await test('F11-02-details-guards',()=>{const {party,inv}=invoice('supplier',900);Auth.user={id:'sales',role:'sales',viewCosts:false,permissions:deep(RolePermissions.sales),active:true};const blocked=[];for(const [name,fn]of [['supplierDetails',()=>Party360.base('supplier',party.id)],['supplierInvoiceForm',()=>Forms.openInvoice('supplierInvoice',{editId:inv.id})],['supplierPrint',()=>Print.invoice(inv.id)],['supplierDisguisedAsCustomer',()=>Forms.openInvoice('customerInvoice',{editId:inv.id})]]){let ok=false;try{fn()}catch(e){ok=e.message.includes('مسموح')}assert(ok,name+' denies access');blocked.push(name)}return {blocked}});
 return results;
 }""")
 (OUT/'guards-domain-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));b.close();s.shutdown()
 if any(x['status']!='PASS' for x in result):raise SystemExit(1)
