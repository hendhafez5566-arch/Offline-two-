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
DB.save=async()=>({indexedDb:true,server:true,serverAvailable:false,cache:true});
const base=structuredClone(DB.data), date=new Date().toISOString().slice(0,10), results=[];
function reset(){DB.data=structuredClone(base);DB._depth=0;DB.syncBlocked=false;Accounting.invalidateLineCache();Auth.user=DB.data.users[0];DB.refreshAuditBaseline()}
function test(name,fn){reset();try{const evidence=fn();results.push({name,...evidence})}catch(e){results.push({name,harnessError:e.message,stack:e.stack.split('\n').slice(0,3)})}}
function invoice(kind,amount,cur='EGP',dt=date){const party=kind==='supplier'?Transactions.addSupplier({name:'probe supplier',currency:cur}):Transactions.addCustomer({name:'probe customer',type:'company'});const inv=Invoices.create({kind,partyId:party.id,partyType:kind==='supplier'?'supplier':'customer',currency:cur,date:dt,lines:[{description:'test',qty:1,price:amount,taxId:'TAX0',accountId:kind==='supplier'?'5100':'4200'}],status:'draft'});Invoices.post(inv);return {party,inv}}
function raw(lines,dt=date){try{const j=Accounting.post({date:dt,lines});return{accepted:true,debit:j.lines.reduce((z,l)=>z+l.baseDebit,0),credit:j.lines.reduce((z,l)=>z+l.baseCredit,0),lines:j.lines}}catch(e){return{accepted:false,error:e.message}}}

let seed=1978;function rng(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296}
function eq(a,b,label){if(Math.abs(a-b)>1e-7)throw new Error(label+': '+a+' vs '+b)}
let tested=0,failed=[];
for(let i=0;i<1200;i++){
 reset();try{
 const cur=i%3===0?'USD':'EGP',kind=i%2?'supplier':'customer';Currency.setRate('USD',50,date);
 Transactions.createTreasury({name:'funded',type:'cash',currency:'EGP',opening:1000000,date,silent:true});const t=DB.data.treasuries.at(-1);
 const amount=Money.round(100+rng()*10000,cur),{party,inv}=invoice(kind,amount,cur);
 const installments=[Money.round(amount*.23,cur),Money.round(amount*.37,cur)],vouchers=[];
 for(const amt of installments){vouchers.push(kind==='supplier'?Transactions.addPayment({partyType:'supplier',partyId:party.id,treasuryId:t.id,amount:amt,currency:cur,date,invoiceId:inv.id}):Transactions.addReceipt({partyType:'customer',partyId:party.id,treasuryId:t.id,amount:amt,currency:cur,date,invoiceId:inv.id}));const rem=Invoices.remaining(inv),ledger=kind==='supplier'?(Accounting.supplierPayable(party.id)[cur]||0):(Accounting.partyReceivable('customer',party.id)[cur]||0);eq(rem,Money.round(ledger,cur),'subledger matches invoice')}
 for(const v of vouchers){if(kind==='supplier')Transactions.voidPayment(v.id,'random undo');else Transactions.voidReceipt(v.id,'random undo')}
 eq(Invoices.remaining(inv),amount,'remaining after undo');Invoices.cancel(inv.id,'random cancel');const bal=kind==='supplier'?(Accounting.supplierPayable(party.id)[cur]||0):(Accounting.partyReceivable('customer',party.id)[cur]||0);eq(Money.round(bal,cur),0,'balance after cancellation');
 for(const j of DB.data.journals){const delta=j.lines.reduce((z,l)=>z+l.baseDebit-l.baseCredit,0);eq(Money.round(delta,'EGP'),0,'exact ledger balance')}
 tested++;
 }catch(e){failed.push({case:i,error:e.message})}
}
console.log(JSON.stringify({cases:1200,passed:tested,failures:failed},null,2));
