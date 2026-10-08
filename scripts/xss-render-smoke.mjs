// Part 6 - dynamic XSS render smoke (no browser).
// Boots the CURRENT src/ in a VM with a recording fake DOM, seeds customers/suppliers/agents/programs/bookings/travelers/
// invoices/vouchers/expenses/Umrah records, overwrites every free-text field with hostile payloads, then renders every page,
// print template, statement, report and edit form and asserts the produced HTML never contains a live payload.
// A payload is "live" when its raw '<', '"' or "'" survive (an escaped payload only contains &lt; &quot; &#39;).
// Limits: this checks the HTML STRINGS handed to innerHTML/Print.show. It is not a real browser (no DOM parsing, no CSP).
import { buildAppCode } from './lib/src-bundle.mjs';
import vm from 'node:vm';
const log = []; // every HTML string written anywhere
const store = new Map(), makeClass = () => ({ add() {}, remove() {}, toggle() { return false; }, contains() { return false; } }), els = new Map();
function el(id = '') {
  if (!els.has(id)) {
    let inner = '';
    const o = { id, classList: makeClass(), style: { cssText: '', setProperty() {} }, dataset: {}, textContent: '', value: '', checked: false, disabled: false, files: [], appendChild() {}, remove() {}, focus() {}, closest() { return null; }, querySelector() { return null; }, querySelectorAll() { return []; }, addEventListener() {}, setAttribute() {}, getAttribute() { return null; }, insertAdjacentHTML(_p, h) { log.push({ via: 'insertAdjacentHTML', id, html: String(h) }); }, replaceChildren() {}, toggleAttribute() {}, removeAttribute() {}, hasAttribute() { return false; }, getBoundingClientRect() { return { width: 0, height: 0, top: 0, left: 0 }; }, contains() { return false; }, matches() { return false; }, scrollIntoView() {}, blur() {}, click() {}, cloneNode() { return el('clone-' + Math.random()); }, prepend() {}, append() {}, after() {}, before() {}, children: [], childNodes: [], parentElement: null, parentNode: null, offsetWidth: 0, offsetHeight: 0, scrollTop: 0, scrollHeight: 0 };
    Object.defineProperty(o, 'innerHTML', { get() { return inner; }, set(v) { inner = String(v); log.push({ via: 'innerHTML', id, html: inner }); }, enumerable: true });
    Object.defineProperty(o, 'outerHTML', { get() { return inner; }, set(v) { log.push({ via: 'outerHTML', id, html: String(v) }); } });
    els.set(id, o);
  }
  return els.get(id);
}
Object.assign(globalThis, { document: { documentElement: { classList: makeClass(), style: { setProperty() {} } }, body: { classList: makeClass(), dataset: {}, style: {} }, activeElement: null, getElementById: el, querySelectorAll() { return []; }, querySelector() { return null; }, addEventListener() {}, createElement() { return el('created-' + Math.random()); } }, window: globalThis, matchMedia: () => ({ matches: false }), location: { protocol: 'file:', reload() {} }, innerWidth: 1440, localStorage: { getItem: k => store.get('l:' + k) ?? null, setItem: (k, v) => store.set('l:' + k, String(v)), removeItem: k => store.delete('l:' + k) }, sessionStorage: { getItem: k => store.get('s:' + k) ?? null, setItem: (k, v) => store.set('s:' + k, String(v)), removeItem: k => store.delete('s:' + k) }, MutationObserver: class { observe() {} disconnect() {} }, confirm: () => true, alert: () => {} });
Object.defineProperty(globalThis, 'navigator', { value: { maxTouchPoints: 0, userAgent: 'ERP-XSS-Smoke', onLine: false }, configurable: true });
Object.defineProperty(globalThis, 'screen', { value: { width: 1440, height: 900 }, configurable: true });
globalThis.window.addEventListener = () => {}; globalThis.window.open = () => null;
const { code, engine } = await buildAppCode();
vm.runInThisContext(code + '\n;globalThis.__x={DB,Auth,Transactions,Invoices,Print,Statements,Reports,Pages,Forms,UI,UmrahDB:UmrahCore_DB,UmrahOps:UmrahCore_Ops,UmrahForms:UmrahCore_Forms};', { filename: 'app.js' });
await new Promise(r => setTimeout(r, 400));
const X = globalThis.__x, { DB, Auth, Transactions, Invoices, Print, Statements, Reports, Pages, Forms } = X;
let failed = 0;
const ok = (n, c, extra = '') => { console.log(`${c ? 'PASS' : 'FAIL'} ${n}${c ? '' : ' ' + extra}`); if (!c) failed++; };
console.log('engine:', engine);

// ---- payloads: one compound payload per field so a single scan catches text, tag and attribute breakouts
let seq = 0; const labels = new Map();
const P = label => { const n = ++seq; labels.set(n, label); return `<img src=x onerror=XSS_${n}>"><script>XSS_${n}</script>' onmouseover='XSS_${n}" autofocus onfocus="XSS_${n}`; };
const LIVE = [/<img src=x onerror=XSS_(\d+)/, /<script>XSS_(\d+)/, /' onmouseover='XSS_(\d+)/, /" autofocus onfocus="XSS_(\d+)/, /" onerror="XSS_(\d+)/];

DB.data.meta.setupComplete = true;
const admin = { id: 'admin-xss', name: 'XSS Admin', role: 'admin', active: true, permissions: { all: true }, approvalLimit: 1e12 };
DB.data.users = [admin]; Auth.user = admin;
if (!DB.data.treasuries.length) Transactions.createTreasury({ name: 'خزنة', type: 'cash', currency: 'EGP', opening: 0, silent: true });
const tre = DB.data.treasuries.find(x => x.currency === 'EGP') || DB.data.treasuries[0];
const date = '2026-11-10', back = '2026-11-20';  // sales close at the departure date, so keep both in the future of the pinned test day

// ---- seed through the real APIs so every relation is valid
const seed = {};
const attempt = (name, f) => { try { seed[name] = f(); } catch (e) { console.log('  seed skipped', name, '-', String(e.message).slice(0, 90)); } };
attempt('cust', () => Transactions.addCustomer({ name: 'C1', phone: '0100', type: 'individual' }));
attempt('sup', () => Transactions.addSupplier({ name: 'S1', currency: 'EGP', type: 'hotel' }));
attempt('agent', () => Transactions.addAgent({ name: 'A1', phone: '0111' }));
attempt('prog', () => Transactions.addProgram({ name: 'P1', type: 'umrah', capacity: 10, currency: 'EGP', departureDate: date, returnDate: back, price: 1000, cost: 500 }));
attempt('book', () => Transactions.addBooking({ customerId: seed.cust.id, programId: seed.prog.id, persons: 2, total: 2000, date, currency: 'EGP', status: 'confirmed' }));
attempt('inv', () => { const i = Invoices.create({ kind: 'customer', partyType: 'customer', partyId: seed.cust.id, currency: 'EGP', date, dueDate: '2026-10-10', lines: [{ description: 'L1', qty: 2, price: 1500, taxId: 'TAX0' }] }); Invoices.post(i); return i; });
attempt('sinv', () => { const i = Invoices.create({ kind: 'supplier', partyType: 'supplier', partyId: seed.sup.id, currency: 'EGP', date, dueDate: '2026-10-10', lines: [{ description: 'L2', qty: 3, price: 800, taxId: 'TAX0' }] }); Invoices.post(i); return i; });
attempt('rec', () => Transactions.addReceipt({ partyType: 'customer', partyId: seed.cust.id, amount: 1000, currency: 'EGP', date, treasuryId: tre.id, method: 'cash', note: 'N1', allocations: seed.inv ? [{ invoiceId: seed.inv.id, amount: 1000 }] : [] }));
attempt('pay', () => Transactions.addPayment({ partyType: 'supplier', partyId: seed.sup.id, amount: 700, currency: 'EGP', date, treasuryId: tre.id, method: 'cash', note: 'N2', allocations: seed.sinv ? [{ invoiceId: seed.sinv.id, amount: 700 }] : [] }));
attempt('exp', () => Transactions.addExpense({ date, category: 'rent', amount: 500, currency: 'EGP', treasuryId: tre.id, mode: 'cash', description: 'E1', taxId: 'TAX0' }));
attempt('svc', () => Transactions.addService({ customerId: seed.cust.id, supplierId: seed.sup.id, type: DB.data.serviceTypes[0].name, description: 'V1', price: 300, cost: 200, currency: 'EGP', date }));
attempt('xfer', () => { if (DB.data.treasuries.length < 2) Transactions.createTreasury({ name: 'خزنة 2', type: 'cash', currency: 'EGP', opening: 0, silent: true }); const t2 = DB.data.treasuries.find(t => t.id !== tre.id).id; return Transactions.transfer({ from: tre.id, to: t2, fromId: tre.id, toId: t2, fromTreasuryId: tre.id, toTreasuryId: t2, amount: 10, currency: 'EGP', date, note: 'T1' }); });
// Umrah
try {
  X.UmrahDB.load();
  const up = X.UmrahOps.createProgram({ programType: 'umrah', name: 'UP1', groupNo: 'G1', departureDate: date, returnDate: back, capacity: 10, currency: 'EGP', defaultTreasuryId: tre.id, holdHours: 24, priceDouble: 12000, status: 'open' });
  seed.up = up;
  X.UmrahOps.addSegment({ programId: up.id, type: 'hotel', title: 'H1', start: date, end: '2026-11-15', nights: 5, supplierId: seed.sup?.id, doubleQty: 5 }, true);
  const ub = X.UmrahOps.createBooking({ programId: up.id, customerId: seed.cust.id, date, adults: 2, primaryRoomType: 'double', status: 'hold', discount: 0 });
  seed.ub = ub; try { X.UmrahOps.confirmBooking(ub.id); } catch (_) {}
} catch (e) { console.log('  umrah seed skipped -', String(e.message).slice(0, 90)); }
ok('seed produced the core records', !!(seed.cust && seed.sup && seed.inv && seed.rec && seed.exp), JSON.stringify(Object.keys(seed)));

// ---- poison every free-text field everywhere
const FREE = /(name|note|memo|desc|address|phone|mobile|email|title|label|reason|remark|comment|city|hotel|route|nationality|passport|company|contact|text|subject|message|group|reference|ref|branch|owner|beneficiary|bank|policy|terms|footer|header|slogan|website|vat|tax(No|Number|Id)?$|registry|license|serial|plate|driver|room|flight|airline|gate|terminal|supplierName|customerName)/i;
const SKIP = /(^id$|Id$|Ids$|currency|status|type$|kind|date|time|token|hash|role|username|password|permission|salt|checksum|signature|key$|^no$|code$|logo|created|updated|revision|version|iso|lang|locale|theme|color|font|icon|mode|method|unit|level|state|stage|source|tab|page|order|index|sort|seq|prefix|suffix)/i;
let poisoned = 0;
const walk = (o, depth = 0, path = '') => {
  if (!o || typeof o !== 'object' || depth > 7) return;
  if (Array.isArray(o)) { o.forEach(v => walk(v, depth + 1, path)); return; }
  for (const k of Object.keys(o)) {
    const v = o[k];
    if (typeof v === 'string' && v && FREE.test(k) && !SKIP.test(k)) { o[k] = P(path + '.' + k); poisoned++; }
    else if (v && typeof v === 'object') walk(v, depth + 1, k);
  }
};
const protectedRoots = new Set(['meta', 'users', 'license', 'sequences', 'umrahMeta', 'umrahSequences', 'currencies', 'fxRates', 'accounts', 'taxCodes', 'serviceTypes']);
for (const k of Object.keys(DB.data)) if (!protectedRoots.has(k)) walk(DB.data[k], 0, k);
// also display-number fields (document numbers can come from imported files)
for (const k of ['invoices', 'receipts', 'payments', 'expenses', 'transfers', 'journals', 'bookings', 'quotations', 'purchaseOrders', 'umrahPrograms', 'umrahBookings', 'programs']) for (const r of DB.data[k] || []) if (typeof r.no === 'string') { r.no = P(k + '.no'); poisoned++; }
DB.data.company = { ...(DB.data.company || {}), name: 'Co', address: 'a', phone: '1', taxNo: '2', commercialNo: '3' }; // company block is printed on every document
walk(DB.data.company, 0, 'company');
{ const n = ++seq; labels.set(n, 'company.logo'); DB.data.company.logo = `data:image/png;base64,AAA" onerror="XSS_${n}`; poisoned++; } // logo is an attribute value (img src), set only through the uploader but also present in imported/synced state
console.log(`poisoned ${poisoned} fields, ${seq} distinct payloads`);

// ---- render everything
const errors = [];
const run = (what, f) => { try { const r = f(); if (typeof r === 'string') log.push({ via: 'return', id: what, html: r }); return r; } catch (e) { errors.push(what + ': ' + String(e.message).slice(0, 80)); } };
const origShow = Print.show; Print.show = function (html, ctx) { log.push({ via: 'Print.show', id: ctx?.type || '', html: String(html) }); try { return origShow.call(this, html, ctx); } catch (e) { errors.push('Print.show: ' + e.message); } };
for (const k of Object.keys(Pages)) run('Pages.' + k, () => Pages[k]());
const ids = c => (DB.data[c] || []).map(r => r.id);
for (const id of ids('invoices')) run('Print.invoice', () => Print.invoice(id));
for (const id of ids('receipts')) run('Print.voucher.receipt', () => Print.voucher('receipt', id));
for (const id of ids('payments')) run('Print.voucher.payment', () => Print.voucher('payment', id));
for (const id of ids('journals')) run('Print.journal', () => Print.journal(id));
for (const id of ids('expenses')) run('Print.expense', () => Print.expense(id));
for (const id of ids('quotations')) run('Print.quotation', () => Print.quotation(id));
for (const id of ids('purchaseOrders')) run('Print.purchaseOrder', () => Print.purchaseOrder(id));
for (const id of ids('transfers')) run('Print.transfer', () => Print.transfer(id));
for (const id of ids('invoiceAdjustments')) run('Print.adjustment', () => Print.adjustment(id));
for (const [t, c] of [['customer', 'customers'], ['supplier', 'suppliers'], ['agent', 'agents']]) for (const id of ids(c)) { run('Print.showStatement.' + t, () => Print.showStatement(t, id)); run('Statements.' + t, () => Statements[t](id)); run('Actions.party360.' + t, () => globalThis.Actions.party360?.(t, id)); }
for (const id of ids('treasuries')) run('Print.showStatement.treasury', () => Print.showStatement('treasury', id));
for (const a of DB.data.accounts || []) run('Print.showStatement.account', () => Print.showStatement('account', a.id));
for (const k of ['income', 'balance', 'tax', 'cashflow', 'programProfit', 'rooming']) run('Reports.' + k, () => Reports[k]?.('2026-01-01', '2026-12-31'));
for (const p of DB.data.programs || []) run('Reports.rooming', () => Reports.rooming?.(p.id));
for (const [k, c] of [['customer', 'customers'], ['supplier', 'suppliers'], ['agent', 'agents'], ['program', 'programs'], ['booking', 'bookings'], ['service', 'services'], ['invoice', 'invoices'], ['receipt', 'receipts'], ['payment', 'payments'], ['expense', 'expenses']]) for (const id of ids(c)) { run('Forms.open.' + k, () => Forms.open(k, id)); }
for (const [k, c] of [['program', 'umrahPrograms'], ['booking', 'umrahBookings'], ['traveler', 'umrahTravelers']]) for (const id of ids(c)) run('UmrahForms.' + k, () => X.UmrahForms[k]?.(id));
for (const f of ['view']) for (const c of ['umrahBookings', 'umrahPrograms', 'umrahTravelers']) for (const id of ids(c)) run('UmrahForms.view', () => X.UmrahForms.view?.(c.replace(/^umrah|s$/gi, '').toLowerCase(), id));
console.log(`rendered ${log.length} HTML writes (${(log.reduce((a, b) => a + b.html.length, 0) / 1024).toFixed(0)} KB); ${errors.length} renderer exceptions (informational)`);

if (process.env.XSS_DEBUG) console.log(errors.join('\n'));
// ---- assertions
const seen = new Set(), leaks = new Map();
for (const w of log) {
  for (const m of w.html.matchAll(/XSS_(\d+)/g)) seen.add(+m[1]);
  for (const re of LIVE) { const m = w.html.match(re); if (m) { const k = labels.get(+m[1]); const key = k + ' <- ' + (w.via + ':' + w.id).slice(0, 40); if (!leaks.has(key)) leaks.set(key, w.html.slice(Math.max(0, m.index - (process.env.XSS_CTX ? 400 : 60)), m.index + 40).replace(/\s+/g, ' ')); } }
  // javascript: URLs in URL-bearing attributes
  for (const m of w.html.matchAll(/\b(?:href|src|action|formaction|xlink:href|data)\s*=\s*["']?\s*(?:javascript|vbscript|data:text\/html)/gi)) leaks.set('javascript-url <- ' + w.via + ':' + w.id, w.html.slice(m.index, m.index + 60));
}
ok('poisoned fields actually reached the rendered output (coverage >= 60 distinct payloads)', seen.size >= 60, `only ${seen.size} of ${seq} payloads were rendered anywhere`);
console.log(`coverage: ${seen.size}/${seq} payloads appeared in rendered output`);
if (process.env.XSS_DEBUG) console.log('NOT RENDERED:', [...labels].filter(([n]) => !seen.has(n)).map(([, l]) => l).join(', '));
const surfaces = new Set(log.map(w => w.via)); console.log('write channels exercised:', [...surfaces].join(', '));
ok('print templates were rendered', log.some(w => w.via === 'Print.show' && /print-company|print-/.test(w.html)));
ok('no live (unescaped) payload anywhere in rendered pages, print templates, statements, reports, forms', leaks.size === 0, '\n  ' + [...leaks].slice(0, 400).map(([k, v]) => k + '\n      ...' + v).join('\n  ') + `\n  (${leaks.size} distinct leak sites)`);
if (failed) { console.error(`\n${failed} check(s) failed`); process.exit(1); }
console.log('\nXSS render smoke passed');
