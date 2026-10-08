import fs from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const store=new Map(),makeClass=()=>({add(){},remove(){},toggle(){return false},contains(){return false}}),els=new Map();
function el(id=''){if(!els.has(id))els.set(id,{id,classList:makeClass(),style:{cssText:'',setProperty(){}},dataset:{},innerHTML:'',textContent:'',value:'',checked:false,disabled:false,files:[],appendChild(){},remove(){},focus(){},closest(){return null},querySelector(){return null},querySelectorAll(){return[]},addEventListener(){},setAttribute(){},getAttribute(){return null}});return els.get(id)}
Object.assign(globalThis,{document:{documentElement:{classList:makeClass(),style:{setProperty(){}}},body:{classList:makeClass(),dataset:{},style:{}},activeElement:null,getElementById:el,querySelectorAll(){return[]},querySelector(){return null},addEventListener(){},createElement(){return el('created-'+Math.random())}},window:globalThis,matchMedia:()=>({matches:false}),location:{protocol:'file:',reload(){}},innerWidth:1440,localStorage:{getItem:k=>store.get('l:'+k)??null,setItem:(k,v)=>store.set('l:'+k,String(v)),removeItem:k=>store.delete('l:'+k)},sessionStorage:{getItem:k=>store.get('s:'+k)??null,setItem:(k,v)=>store.set('s:'+k,String(v)),removeItem:k=>store.delete('s:'+k)},MutationObserver:class{observe(){} disconnect(){}},confirm:()=>true,alert:()=>{}});
Object.defineProperty(globalThis,'navigator',{value:{maxTouchPoints:0,userAgent:'ERP-Smoke-Test',onLine:false},configurable:true});
Object.defineProperty(globalThis,'screen',{value:{width:1440,height:900},configurable:true});
globalThis.window.addEventListener=()=>{};globalThis.window.open=()=>null;
const {registerHooks}=await import('node:module');
registerHooks({resolve(specifier,context,next){if(specifier.startsWith('.')&&context.parentURL?.endsWith('.ts')&&!/\.[a-z]+$/.test(specifier)){try{return next(specifier+'.ts',context)}catch(e){return next(specifier+'/index.ts',context)}}return next(specifier,context)}});
await import('../src/main.ts');await new Promise(r=>setTimeout(r,400));
globalThis.__erp={DB:globalThis.DB,Accounting:globalThis.Accounting,Invoices:globalThis.Invoices,Transactions:globalThis.Transactions,Auth:globalThis.Auth,Currency:globalThis.Currency,CRM:globalThis.CRM};
const {DB,Accounting,Invoices,Transactions,Auth,Currency,CRM}=globalThis.__erp;
DB.data.meta.setupComplete=true;const admin={id:'admin-smoke',name:'Smoke Admin',role:'admin',active:true,permissions:{all:true},approvalLimit:1e12};DB.data.users=[admin];Auth.user=admin;if(!DB.data.treasuries.length)Transactions.createTreasury({name:'خزنة الاختبار',type:'cash',currency:'EGP',opening:0,silent:true});

const {Money,Periods}=globalThis;
DB.save=async()=>{globalThis.Commercial.beforeSave();return {indexedDb:true,server:true,serverAvailable:false,cache:true}};
const base=structuredClone(DB.data), date=new Date().toISOString().slice(0,10), results=[];
function reset(){DB.data=structuredClone(base);DB._depth=0;DB.syncBlocked=false;Accounting.invalidateLineCache();Auth.user=DB.data.users[0];DB.refreshAuditBaseline()}
function test(name,fn){reset();try{const evidence=fn();results.push({name,...evidence})}catch(e){results.push({name,harnessError:e.message,stack:e.stack.split('\n').slice(0,3)})}}
function invoice(kind,amount,cur='EGP',dt=date){const party=kind==='supplier'?Transactions.addSupplier({name:'probe supplier',currency:cur}):Transactions.addCustomer({name:'probe customer',type:'company'});const inv=Invoices.create({kind,partyId:party.id,partyType:kind==='supplier'?'supplier':'customer',currency:cur,date:dt,lines:[{description:'test',qty:1,price:amount,taxId:'TAX0',accountId:kind==='supplier'?'5100':'4200'}],status:'draft'});Invoices.post(inv);return {party,inv}}
function raw(lines,dt=date){try{const j=Accounting.post({date:dt,lines});return{accepted:true,debit:j.lines.reduce((z,l)=>z+l.baseDebit,0),credit:j.lines.reduce((z,l)=>z+l.baseCredit,0),lines:j.lines}}catch(e){return{accepted:false,error:e.message}}}

const {AdvancedAccounting,Approvals,Backup,Attachments,AttachmentStore,ServerStore,BranchScope,Commercial,Pages,UI,Statements,Reports,MasterData,UmrahCore_DB:UDB,UmrahCore_Ops:UOps,UmrahCore_ContractCenter:UCC}=globalThis;
const diary=[];const evidence={};
function check(v,label,actual){if(!v)throw Object.assign(new Error(label),{actual})}
function near(a,b,label){check(Math.abs(a-b)<.000001,label,{actual:a,expected:b})}
function blocked(fn,label){let err;try{fn()}catch(e){err=e.message}check(!!err,label);return err}
async function scene(name,fn){reset();UDB.load();try{const facts=await fn();diary.push({name,status:'PASS',facts})}catch(e){diary.push({name,status:'FAIL',error:e.message,actual:e.actual,stack:e.stack.split('\n').slice(0,4)})}}
function funded(){return Transactions.createTreasury({name:'خزنة الشركة',type:'bank',currency:'EGP',opening:500000,date,silent:true})}
function taxInv(kind,amount,recognitionDate=''){const party=kind==='supplier'?Transactions.addSupplier({name:'فندق الأمانة',currency:'EGP'}):Transactions.addCustomer({name:'شركة النور',type:'company'});const inv=Invoices.create({kind,partyId:party.id,partyType:kind==='supplier'?'supplier':'customer',currency:'EGP',date,recognitionDate,lines:[{description:'خدمة متفق عليها',qty:1,price:amount,taxId:'VAT14',accountId:kind==='supplier'?'5100':'4200'}],status:'draft'});Invoices.post(inv);return{party,inv}}
const {Tax}=globalThis;
const {UmrahCore_Bridge:UB,UmrahCore_Procurement:UP,UmrahCore_Cost:UC}=globalThis;
const snapshots=[];function snap(label,obj){snapshots.push({label,...obj})}
function prog({capacity=20,price=45000,currency='EGP',name='عمرة نوفمبر',depositMin=0}={}){if(currency!=='EGP'){Currency.setRate(currency,currency==='USD'?50:13.25,date);Currency.setRate(currency,currency==='USD'?50:13.25,'2026-11-10')};const t=Transactions.createTreasury({name:'خزنة '+currency,type:'bank',currency,opening:500000,date,silent:true}),sp=Transactions.addSupplier({name:'شركة خدمات العمرة',currency});if(currency!=='EGP'){Currency.setRate(currency,currency==='USD'?50:13.25,date);Currency.setRate(currency,currency==='USD'?50:13.25,'2026-11-10')};const p=UOps.createProgram({programType:'umrah',name,departureDate:'2026-11-10',returnDate:'2026-11-20',capacity,currency,defaultTreasuryId:t.id,holdHours:24,depositMin,priceDouble:price,priceQuad:price-(currency==='EGP'?5000:currency==='USD'?100:377.36),priceTriple:price-(currency==='EGP'?2500:currency==='USD'?50:188.68),priceSingle:price+(currency==='EGP'?15000:currency==='USD'?300:1132.08),childBed:currency==='EGP'?30000:currency==='USD'?600:2264.15,childNoBed:currency==='EGP'?18000:currency==='USD'?360:1358.49,infant:currency==='EGP'?5000:currency==='USD'?100:377.36,status:'open'});const hotel=UOps.addSegment({programId:p.id,type:'hotel',title:'فندق مكة',start:'2026-11-10',end:'2026-11-19',nights:10,supplierId:sp.id,singleQty:capacity,doubleQty:Math.ceil(capacity/2),tripleQty:Math.ceil(capacity/3),quadQty:Math.ceil(capacity/4)},true),out=UOps.addSegment({programId:p.id,type:'flight',title:'ذهاب القاهرة جدة',start:'2026-11-10',end:'2026-11-10',supplierId:sp.id,seats:capacity},true),ret=UOps.addSegment({programId:p.id,type:'flight',title:'عودة جدة القاهرة',start:'2026-11-20',end:'2026-11-20',supplierId:sp.id,seats:capacity},true);return{p,t,sp,hotel,out,ret}}
function book(p,c,adults=2,extra={}){return UOps.createBooking({date,programId:p.id,customerId:c.id,adults,childBed:0,childNoBed:0,infants:0,primaryRoomType:'double',status:'confirmed',discount:0,...extra})}
function invOf(b){return DB.data.invoices.find(x=>x.id===UOps.booking(b.id).hostInvoiceId)}
function deposit(b,t,amount,key){return UB.emit('umrah.booking.deposit.requested',{bookingId:b.id,bookingNo:b.no,date,amount,currency:b.currency,treasuryId:t.id,paymentMethod:'cash'},key||'deposit:'+b.id+':'+amount)}


function fx(cur,dt=date,rate){if(!Currency.get(cur))DB.data.currencies.push({code:cur,name:cur,decimals:cur==='BHD'?3:2,active:true});if(cur!=='EGP')Currency.setRate(cur,rate??(cur==='USD'?50:cur==='SAR'?13.25:130),dt)}
function makeInv(kind,amount,cur='EGP',party,dateValue=date){fx(cur);party??=kind==='supplier'?Transactions.addSupplier({name:'مورد مراجعة',currency:cur}):Transactions.addCustomer({name:'عميل مراجعة'});const inv=Invoices.create({kind,partyId:party.id,partyType:kind==='supplier'?'supplier':'customer',currency:cur,date:dateValue,lines:[{description:'خدمة مراجعة',qty:1,price:amount,taxId:'TAX0',accountId:kind==='supplier'?'5100':'4200'}],status:'draft'});Invoices.post(inv);return{party,inv}}


// ===== v32.5.69 acceptance: 8 real-flow cases, independent hand-computed expectations =====
const D0='2026-10-01',D1='2026-10-03',D2='2026-10-05',D3='2026-10-06';
const allLines=()=>Accounting.lines('','2099-12-31');
const sumAcct=(id,f=allLines())=>{let d=0,c=0;for(const l of f)if(l.accountId===id){d+=l.baseDebit||0;c+=l.baseCredit||0}return +(d-c).toFixed(6)};
const accType=id=>Accounting.account(id)?.type;
const plNet=()=>{let v=0;for(const l of allLines()){const t=accType(l.accountId);if(t==='revenue'||t==='expense')v+=(l.baseCredit||0)-(l.baseDebit||0)}return +v.toFixed(6)};
const jBalanced=()=>{const bad=[];for(const j of DB.data.journals){let d=0,c=0;for(const l of j.lines){for(const k of ['debit','credit','baseDebit','baseCredit'])if(l[k]!==undefined&&!Number.isFinite(l[k]))bad.push({j:j.no,k:l[k]});d+=l.baseDebit||0;c+=l.baseCredit||0}if(Math.abs(d-c)>0.005)bad.push({j:j.no,refType:j.refType,d,c})}return bad};
function eq(a,b,label,tol=0.0051){check(Math.abs(a-b)<tol,label,{actual:a,expected:b})}
function noRawImbalance(label){const bad=jBalanced();check(bad.length===0,label+': raw journal imbalance/non-finite',bad)}
function unchanged(before,label){check(JSON.stringify(DB.data)===before,label+': state changed after rejected/failed operation')}
const snapJson=()=>JSON.stringify(DB.data);
function cust(n='عميل'){return Transactions.addCustomer({name:n})}
function sinv(c,price,{cur='EGP',dt=D0,tax='TAX0'}={}){const i=Invoices.create({kind:'customer',partyId:c.id,partyType:'customer',currency:cur,date:dt,lines:[{description:'خدمة',qty:1,price,taxId:tax,accountId:'4200'}],status:'draft'});Invoices.post(i);return i}
function bank(cur='EGP',opening=0){return Transactions.createTreasury({name:'خزنة '+cur,type:'bank',currency:cur,opening,date:D0,silent:true})}
const tbal=t=>Accounting.treasuryBalance(t.id);

await scene('1) سداد جزئي ثم كامل بعملة أجنبية مع تغير السعر',()=>{
 fx('USD',D0,50);fx('USD',D1,51.37);fx('USD',D2,49.13);const t=bank('USD'),c=cust(),inv=sinv(c,1000,{cur:'USD'});
 eq(sumAcct('1200'),50000,'AR after invoice');
 const r1=Transactions.addReceipt({date:D1,partyType:'customer',partyId:c.id,treasuryId:t.id,amount:400,currency:'USD',invoiceId:inv.id});
 eq(Invoices.remaining(inv),600,'remaining after partial');eq(sumAcct('1200'),30000,'AR carried at invoice rate 600*50');eq(tbal(t),400,'bank native');
 const r2=Transactions.addReceipt({date:D2,partyType:'customer',partyId:c.id,treasuryId:t.id,amount:600,currency:'USD',invoiceId:inv.id});
 eq(Invoices.remaining(inv),0,'remaining zero');eq(sumAcct('1200'),0,'AR zero');eq(tbal(t),1000,'bank native 1000');
 const cashBase=allLines().filter(l=>l.treasuryId===t.id).reduce((z,l)=>z+(l.baseDebit||0)-(l.baseCredit||0),0);
 eq(cashBase,400*51.37+600*49.13,'cash base = 20548+29478');eq(plNet(),50026,'P&L = revenue 50000 + realized FX 26');
 noRawImbalance('c1');Transactions.voidReceipt(r2.id,'عكس');eq(Invoices.remaining(inv),600,'remaining after void');eq(sumAcct('1200'),30000,'AR after void');eq(tbal(t),400,'bank after void');noRawImbalance('c1 void');
 return {cashBase,pl:plNet()}});

await scene('2) مقدم عميل: استخدام جزء ورد الباقي',()=>{
 const t=bank('EGP'),c=cust(),inv=sinv(c,6000,{dt:D1});
 const r=Transactions.addReceipt({date:D0,partyType:'customer',partyId:c.id,treasuryId:t.id,amount:10000,currency:'EGP',invoiceId:inv.id});
 eq(Invoices.remaining(inv),0,'invoice settled by advance');eq(Accounting.customerAdvance('customer',c.id).EGP||0,4000,'advance left 4000');eq(sumAcct('1200'),0,'AR zero');eq(sumAcct('2400'),-4000,'advance liability 4000 credit');eq(tbal(t),10000,'cash');
 const before=snapJson();blocked(()=>Transactions.addPayment({date:D3,partyType:'customerAdvance',partyId:c.id,treasuryId:t.id,amount:4000.01,currency:'EGP'}),'refund beyond advance rejected');unchanged(before,'over-refund');
 Transactions.addPayment({date:D3,partyType:'customerAdvance',partyId:c.id,treasuryId:t.id,amount:4000,currency:'EGP'});
 eq(Accounting.customerAdvance('customer',c.id).EGP||0,0,'advance zero');eq(tbal(t),6000,'cash 6000');eq(sumAcct('2400'),0,'2400 zero');eq(plNet(),6000,'revenue 6000');noRawImbalance('c2');return {}});

await scene('3) إشعار دائن وعكسه',()=>{
 const c=cust(),inv=sinv(c,1000,{tax:'VAT14'}),taxAcc=Tax.require('VAT14').outputAccount;
 eq(Invoices.remaining(inv),1140,'gross 1140');eq(sumAcct(taxAcc),-140,'tax 140');
 const a=Invoices.adjust(inv.id,'credit',570,'نصف',D1);
 eq(Invoices.remaining(inv),570,'remaining 570');eq(sumAcct('1200'),570,'AR 570');eq(sumAcct(taxAcc),-70,'tax 70');eq(sumAcct('4200'),-500,'revenue 500');noRawImbalance('c3 credit');
 const before=snapJson();blocked(()=>Invoices.adjust(inv.id,'credit',570.01,'زيادة',D1),'credit beyond net rejected');unchanged(before,'over-credit');
 Invoices.reverseAdjustment(a,'عكس');
 eq(Invoices.remaining(inv),1140,'restored');eq(sumAcct('1200'),1140,'AR restored');eq(sumAcct(taxAcc),-140,'tax restored');eq(sumAcct('4200'),-1000,'revenue restored');noRawImbalance('c3 reverse');
 const t=bank();Transactions.addReceipt({date:D1,partyType:'customer',partyId:c.id,treasuryId:t.id,amount:1140,currency:'EGP',invoiceId:inv.id});
 const b=Invoices.adjust(inv.id,'credit',114,'بعد السداد',D2);eq(Accounting.customerAdvance('customer',c.id).EGP||0,114,'overpaid credit becomes advance 114');
 Invoices.reverseAdjustment(b,'عكس');eq(Accounting.customerAdvance('customer',c.id).EGP||0,0,'advance gone');eq(Invoices.remaining(inv),0,'paid');noRawImbalance('c3 paid');return {}});

await scene('4) إعادة تقييم ثم سداد الرصيد',()=>{
 fx('USD',D0,50);fx('USD',D1,52);fx('USD',D2,53);const t=bank('USD'),c=cust(),inv=sinv(c,1000,{cur:'USD'});
 Accounting.fxRevalue(D1);eq(sumAcct('1200'),52000,'AR revalued to 52000');eq(sumAcct('4510'),-2000,'unrealized gain 2000');
 Transactions.addReceipt({date:D2,partyType:'customer',partyId:c.id,treasuryId:t.id,amount:1000,currency:'USD',invoiceId:inv.id});
 eq(Invoices.remaining(inv),0,'remaining zero');eq(sumAcct('1200'),0,'AR base zero after settle');eq(tbal(t),1000,'bank 1000 USD');
 const cashBase=allLines().filter(l=>l.treasuryId===t.id).reduce((z,l)=>z+(l.baseDebit||0)-(l.baseCredit||0),0);
 eq(cashBase,53000,'cash base 53000');eq(plNet(),53000,'P&L 50000+2000+1000');noRawImbalance('c4');
 const msg=blocked(()=>Accounting.fxRevalue(D3),'no second revaluation diff');return {msg}});

await scene('5) إيراد مؤجل: اعتراف جزئي ثم إلغاء الباقي',()=>{
 const c=cust(),inv=sinv(c,3000,{dt:D0});
 AdvancedAccounting.deferInvoiceRevenue({invoiceId:inv.id,date:D0,recognitionDate:D2,months:3});
 const s=DB.data.deferredRevenueSchedules.find(x=>x.invoiceId===inv.id);check(s&&s.parts.length===3&&s.parts.every(p=>p.amount===1000),'3 parts of 1000',s);
 eq(sumAcct('2700'),-3000,'deferred 3000');eq(sumAcct('4200'),0,'no revenue yet');
 AdvancedAccounting.recognizeDeferredPart(s.id,s.parts[0].id);
 eq(sumAcct('2700'),-2000,'deferred 2000');eq(sumAcct('4200'),-1000,'revenue 1000');
 let before=snapJson();blocked(()=>Invoices.cancel(inv.id,'إلغاء الباقي'),'cancel after partial recognition rejected');unchanged(before,'cancel rejected');
 before=snapJson();blocked(()=>Invoices.adjust(inv.id,'credit',2000,'إلغاء الباقي',D3),'credit of remainder rejected after recognition');unchanged(before,'credit rejected');
 AdvancedAccounting.reverseDeferredPart(s.id,s.parts[0].id,'عكس الاعتراف');Invoices.cancel(inv.id,'إلغاء كامل');
 eq(sumAcct('2700'),0,'2700 zero');eq(sumAcct('4200'),0,'revenue zero');eq(sumAcct('1200'),0,'AR zero');check(DB.data.deferredRevenueSchedules.find(x=>x.id===s.id).status==='void','schedule void');noRawImbalance('c5');return {}});

await scene('6) حجز عمرة ثم إلغاء ورد المبلغ',()=>{
 const {p,t}=prog(),c=cust('معتمر'),b=book(p,c),inv0=invOf(b);deposit(b,t,30000);
 eq(tbal(t),530000,'cash 500000+30000');eq(Invoices.remaining(inv0),60000,'remaining 90000-30000');
 UOps.requestCancel(b.id,'إلغاء العميل');check(UOps.booking(b.id).status==='cancelRequested','awaiting refund/credit');
 Invoices.adjust(inv0.id,'credit',90000,'إلغاء الخدمة بالكامل',D1);
 let before=snapJson();blocked(()=>UOps.completeCancel(b.id),'completeCancel before refund rejected');check(UOps.booking(b.id).status==='cancelRequested','still cancelRequested');
 Transactions.addPayment({date:D1,partyType:'customerAdvance',partyId:c.id,treasuryId:t.id,amount:30000,currency:'EGP',note:'رد المقدم'});
 UOps.completeCancel(b.id);check(UOps.booking(b.id).status==='cancelled','cancelled');
 eq(tbal(t),500000,'cash back to 500000');eq(Accounting.customerAdvance('customer',c.id).EGP||0,0,'advance zero');eq(Accounting.partyReceivable('customer',c.id).EGP||0,0,'receivable zero');eq(Invoices.remaining(inv0),0,'invoice zero');eq(UOps.reservedPersons(p.id),0,'seats released');eq(plNet(),0,'no net revenue');noRawImbalance('c6');return {}});

await scene('7) فشل محقون بعد بدء تعديل حجز عمرة: تراجع كامل وإعادة محاولة',()=>{
 const {p}=prog(),c=cust('معتمر'),b=book(p,c,2,{status:'hold'});check(UOps.booking(b.id).status==='hold','hold');
 const opts={programId:p.id,customerId:c.id,adults:4,childBed:0,childNoBed:0,infants:0,primaryRoomType:'double',discount:0};
 const before=snapJson(),auditBefore=DB.data.auditLog.length,facts={};
 for(const method of ['syncTravelers','ensureHotelRooms']){const orig=UOps[method];let hit=0;UOps[method]=function(...a){hit++;throw new Error('INJECTED:'+method)};
  let err;try{UOps.updateBooking(b.id,opts)}catch(e){err=e.message}finally{UOps[method]=orig}
  check(hit>=1&&err==='INJECTED:'+method,'injection reached after edit started: '+method,{hit,err});unchanged(before,'rollback after '+method);check(DB.data.auditLog.length===auditBefore,'no audit residue');facts[method]='rolled-back';}
 check(UOps.booking(b.id).persons===2,'persons still 2');
 const r=UOps.updateBooking(b.id,opts);check(r.persons===4&&UOps.booking(b.id).counts.adults===4,'retry applied');eq(UOps.booking(b.id).total,4*45000,'total = 4 x 45000');
 check(DB.data.umrahTravelers.filter(x=>x.bookingId===b.id).length===4,'4 travelers after retry');noRawImbalance('c7');return facts});

const failed=diary.filter(x=>x.status==='FAIL');
console.log(JSON.stringify({cases:diary.length,passed:diary.length-failed.length,failed:failed.length,diary},null,1));
process.exit(failed.length?1:0);
