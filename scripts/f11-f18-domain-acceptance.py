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
 // ledger oracle sums raw persisted entries, including reversals; no displayed balance as oracle.
 const rawBalance=(acct,pid,cur,native=false)=>DB.data.journals.filter(j=>!['draft','void','cancelled'].includes(j.status)).flatMap(j=>j.lines).filter(l=>l.accountId===acct&&l.partyId===pid&&l.currency===cur&&(!native||!l.baseOnly)).reduce((z,l)=>z+(native?l.debit-l.credit:l.baseDebit-l.baseCredit),0);
 await test('F14-01',()=>{const out=[];for(const kind of ['customer','supplier'])for(const rates of [[13.25,14,15],[15,14,13.25]]){
  const suffix=kind+rates[0];Currency.setRate('SAR',rates[0],date);const cash=treasury('SAR',1000);const {party,inv}=invoice(kind,100,'SAR');
  Currency.setRate('SAR',rates[1],date);const add=(amount)=>kind==='customer'?Transactions.addReceipt({partyType:'customer',partyId:party.id,treasuryId:cash.id,amount,currency:'SAR',invoiceId:inv.id,date}):Transactions.addPayment({partyType:'supplier',partyId:party.id,treasuryId:cash.id,amount,currency:'SAR',invoiceId:inv.id,date},{ignoreApproval:true});
  const reverse=v=>kind==='customer'?Transactions.voidReceipt(v.id,'QA reversal'):Transactions.voidPayment(v.id,'QA reversal');
  const v1=add(40);Currency.setRate('SAR',rates[2],date);const v2=add(60);reverse(v2);Accounting.fxRevalue(date);const count=DB.data.journals.length;try{Accounting.fxRevalue(date)}catch(e){}assert(DB.data.journals.length===count,'repeat revaluation');
  const v3=add(60);reverse(v3);reverse(v1);Invoices.cancel(inv.id,'QA cancelled');const acct=kind==='supplier'?'2100':'1200';
  near(rawBalance(acct,party.id,'SAR',true),0,'native zero '+suffix);near(rawBalance(acct,party.id,'SAR'),0,'carrying zero '+suffix);
  const c=DB.data.journals.length;Accounting.closeZeroPartyPosition?.(acct,kind,party.id,'SAR');assert(DB.data.journals.length===c,'repeat close idempotent');
  out.push({kind,rates,native:0,carrying:0});
 }return out});
 await test('F18-01',()=>{const out=[];const sp=Transactions.addSupplier({name:'QA supplier',currency:'EGP'});
 for(const cancelled of [0,1,2]){const po=CRM.addPO({supplierId:sp.id,currency:'EGP',date,lines:[{description:'QA units',qty:3,price:200,taxId:'TAX0'}]});CRM.approvePO(po.id);const ids=[];
 for(let n=1;n<=3;n++){CRM.receivePOLines(po.id,{[po.lines[0].id]:n});ids.push(CRM.convertPO(po.id).id)}
 const old=DB.data.invoices.find(i=>i.id===ids[cancelled]);Invoices.cancel(old.id,'QA cancel partial batch');const replacement=CRM.convertPO(po.id);assert(!ids.includes(replacement.id),'replacement created');assert(replacement.externalNo.endsWith('-P4'),'new historical sequence');near(po.lines[0].invoicedQty,3,'quantity fully billed');const total=DB.data.invoices.filter(i=>i.sourceId===po.id&&!['void','cancelled'].includes(i.status)).reduce((z,i)=>z+Invoices.total(i),0);near(total,600,'net active cost');const count=DB.data.invoices.length;try{CRM.convertPO(po.id)}catch(e){}assert(DB.data.invoices.length===count,'repeat no duplicate');out.push({cancelled,externalNo:replacement.externalNo,activeCost:600})}return out});
 const tourism=()=>{const U=UmrahCore_DB.data,branch=DB.data.branches[0]?.id;U.programs.push({id:'qa-p',no:'UP-QA',name:'QA program',currency:'EGP',departureDate:'2026-11-10',returnDate:'2026-11-17',capacity:10,status:'open',active:true,branchId:branch,pricing:{double:8000}});U.programSegments.push({id:'qa-f1',programId:'qa-p',type:'flight',title:'Out',start:'2026-11-10',end:'2026-11-10',active:true,supplierId:'qa-s'},{id:'qa-f2',programId:'qa-p',type:'flight',title:'Return',start:'2026-11-17',end:'2026-11-17',active:true,supplierId:'qa-s'});U.programCosts.push({id:'qa-cost',programId:'qa-p',category:'flight',active:true,supplierId:'qa-s',amount:100,procurementPolicy:'perConfirmedPax',actualizationPolicy:'manual'});U.bookings.push({id:'qa-b1',no:'UB-QA1',programId:'qa-p',status:'confirmed',counts:{adults:2},persons:2,total:16000,currency:'EGP',branchId:branch},{id:'qa-b0',no:'UB-QA0',programId:'qa-p',status:'cancelled',persons:1,currency:'EGP',branchId:branch});U.travelers.push({id:'qa-t1',no:'QA1',nameAr:'QA One',programId:'qa-p',bookingId:'qa-b1',active:true,category:'adult',branchId:branch},{id:'qa-t2',no:'QA2',nameAr:'QA Two',programId:'qa-p',bookingId:'qa-b1',active:true,category:'adult',branchId:branch},{id:'qa-t0',no:'QA0',nameAr:'QA Old',programId:'qa-p',bookingId:'qa-b0',active:true,passportNo:'QA-PASS',branchId:branch});return U};
 await test('F13-01',()=>{const U=tourism(),put=(trav,seg,no,status='issued',seat='12A')=>UmrahCore_Ops.upsertTicket({travelerId:trav,segmentId:seg,pnr:'QA-PNR',ticketNo:no,status,seat});
 put('qa-t1','qa-f1','QA-1');let rejected=false;try{put('qa-t2','qa-f1','QA-2')}catch(e){rejected=true}assert(rejected&&U.tickets.length===1,'same seat rejected');put('qa-t2','qa-f2','QA-2');put('qa-t1','qa-f1','QA-1','cancelled');put('qa-t2','qa-f1','QA-3');return {duplicateRejected:true,otherSectorAllowed:true,cancelledSeatReusable:true}});
 await test('F13-02',()=>{const U=tourism();UmrahCore_Ops.upsertTicket({travelerId:'qa-t1',segmentId:'qa-f1',pnr:'QA',ticketNo:'QA-OLD',status:'issued'});const j=DB.data.journals.length;
 const x=UmrahCore_Ops.upsertTicket({travelerId:'qa-t1',segmentId:'qa-f1',pnr:'QA',ticketNo:'QA-NEW',status:'reissued'});assert(x.history.some(h=>h.before.ticketNo==='QA-OLD'&&h.after.ticketNo==='QA-NEW'&&h.userId==='qa'&&h.at),'reissue history');UmrahCore_Ops.upsertTicket({travelerId:'qa-t1',segmentId:'qa-f1',pnr:'QA',ticketNo:'QA-NEW',status:'reissued'});assert(x.history.length===2,'unchanged save no history duplicate');assert(DB.data.journals.length===j,'no new cost');return {history:x.history,noDuplicateCost:true}});
 await test('F13-03',()=>{const U=tourism();UmrahCore_Ops.updateTraveler('qa-t1',{nameAr:'QA New',passportNo:'QA-PASS'});let blocked=false;try{UmrahCore_Ops.updateTraveler('qa-t2',{nameAr:'QA Second',passportNo:'QA-PASS'})}catch(e){blocked=true}assert(blocked,'active duplicate rejected');assert(U.travelers.find(t=>t.id==='qa-t0').passportNo==='QA-PASS','history retained');return {cancelledReuse:true,activeDuplicateBlocked:true,historyRetained:true}});
 await test('F16-01',()=>{const bank=Transactions.createTreasury({name:'QA Bank',type:'bank',currency:'EGP',opening:100000,date,silent:true});const before=DB.data.journals.length;AdvancedAccounting.importBankLines({treasuryId:bank.id,lines:[{date,amount:100000,reference:'Unique opening'},{date,amount:777,reference:'No match'}]});const r=AdvancedAccounting.reconcileBankLines(bank.id);assert(r.matched===1&&r.unmatched===1,'unique only');assert(DB.data.journals.length===before,'no journals');const repeat=AdvancedAccounting.reconcileBankLines(bank.id);assert(repeat.matched===0,'repeat idempotent');return {matched:1,unmatched:1,newJournals:0}});
 return results;
 }""")
 name='baseline-domain-results.json' if baseline else 'domain-results.json';(OUT/name).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False,indent=2));b.close();s.shutdown()
 if any(r['status']=='FAIL' for r in result):raise SystemExit(1)
