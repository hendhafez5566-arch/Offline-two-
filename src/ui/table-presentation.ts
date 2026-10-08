import { S, esc, icon } from '../core/runtime';

/** One table shell shared by pre-rendered lists and lazy record lists. */
const TablePresentation = {
 shell({headers,rows,empty,count,total,key='',pager='',search=true,exportable=false,page=''}:{headers:any[];rows:string[];empty:string;count:string;total:number;key?:string;pager?:string;search?:boolean;exportable?:boolean;page?:string}){
  const action=(h:any)=>/إجراء|الإجراءات|actions?/i.test(S(h)),preference=JSON.stringify([page,...headers.map(S)]);
  const columns=headers.map((h,i)=>`<label><input type="checkbox" checked data-ui-table-column="${i}" ${action(h)?'disabled':''}> ${esc(h)}</label>`).join('');
  const ths=headers.map((h,i)=>`<th class="${action(h)?'':'sortable'}" data-export="${action(h)?'0':'1'}" ${action(h)?'':`data-ui-sort-index="${i}"`}>${h}</th>`).join('');
  return `<div class="table-card" data-column-key="${esc(preference)}" ${key?`data-lazy-table="${esc(key)}"`:''}><div class="table-tools"><span class="table-count" data-total="${total}">${count}</span>${search?`<div class="table-search">${icon('search','sm')}<input aria-label="بحث داخل الجدول" placeholder="بحث بالاسم أو الرقم…" data-ui-filter-table="1"></div>`:''}<details class="table-column-menu"><summary class="btn small ghost">الأعمدة</summary><div>${columns}</div></details>${exportable?`<button class="btn small ghost" data-ui-export-table="1">${icon('csv','sm')} CSV</button>`:''}</div><div class="table-wrap"><table class="table"><thead><tr>${ths}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}" class="empty">${empty}</td></tr>`}</tbody></table></div>${pager}</div>`;
 }
};
export { TablePresentation };
