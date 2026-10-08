import { TablePresentation } from './table-presentation';
import { N, S, icon, today } from '../core/runtime';
import { AccessControl } from '../security/access-control';
import { UI_Tables } from './ui-tables';
// v32.5.5 — true lazy list rendering. Keep raw records in memory and only build HTML for the visible page.
const UI_DataTables = {
dataTable:function(headers,items,rowRenderer,empty='لا توجد بيانات',opts:any={}){
  const list=Array.isArray(items)?items:[],noSort=h=>/إجراء|الإجراءات|actions?/i.test(S(h)),ths=headers.map((h,i)=>`<th class="${noSort(h)?'':'sortable'}" data-export="${noSort(h)?'0':'1'}" ${noSort(h)?'':`data-ui-sort-index="${i}"`}>${h}</th>`).join(''),pageSize=Math.max(10,N(opts.pageSize)||25),key=`ui-data-${++this._lazySeq}`,shown=list.slice(0,pageSize),render=x=>S(rowRenderer(x));
  const rec={kind:'data',rows:list,filtered:list.slice(),page:1,pageSize,headers:[...headers],empty,query:'',rowRenderer:render,searchText:typeof opts.searchText==='function'?opts.searchText:null,sortValues:Array.isArray(opts.sortValues)?opts.sortValues:[],exportValues:typeof opts.exportValues==='function'?opts.exportValues:null,searchIndex:null,searchIndexBuilding:false};
  this._lazyTables.set(key,rec);
  // Build large-table search text gradually after first paint. This keeps the
  // first keystroke from paying the full indexing cost while preserving the
  // exact same matching semantics and result order.
  if(list.length>=1000&&rec.searchText){
    rec.searchIndexBuilding=true;
    const idx=new Array(list.length),chunk=750;
    let pos=0;
    const step=()=>{
      const end=Math.min(list.length,pos+chunk);
      for(;pos<end;pos++)idx[pos]=this.dataTableSearchValue(rec,list[pos]);
      if(pos<list.length){setTimeout(step,0);return}
      if(!rec.query){rec.searchIndex=idx;rec.searchIndexBuilding=false}
    };
    setTimeout(step,0);
  }
  const htmlRows=shown.map(render),pager=this.tablePager(key,rec),count=list.length?(list.length>pageSize?`1–${shown.length} من ${list.length} سجل`:`${list.length} سجل`):'0 سجل';
  return TablePresentation.shell({headers,rows:htmlRows,empty,count,total:list.length,key,pager,search:opts.search!==false,exportable:opts.export!==false&&AccessControl.can(this.current,'export'),page:this.current});
},

dataTableSearchValue:function(rec,item){
  if(rec.searchText){try{return this.searchNormalize(rec.searchText(item))}catch{return''}}
  return this.searchBlob(item);
},

renderTablePage:function(key,card){
  const rec=this._lazyTables.get(key);
  if(!rec||rec.kind!=='data')return UI_Tables.renderTablePage.call(this,key,card);
  if(!card)return false;
  const total=rec.filtered.length,pages=Math.max(1,Math.ceil(total/rec.pageSize));
  rec.page=Math.min(Math.max(1,rec.page),pages);
  const from=(rec.page-1)*rec.pageSize,to=Math.min(total,from+rec.pageSize),items=rec.filtered.slice(from,to),rows=items.map(rec.rowRenderer),body=card.querySelector('tbody');
  body.innerHTML=rows.length?rows.join(''):`<tr><td colspan="${rec.headers.length}" class="empty">${rec.empty}</td></tr>`;
  const count=card.querySelector('.table-count');if(count)count.textContent=total?(rec.query?`${from+1}–${to} من ${total} نتيجة`:`${from+1}–${to} من ${total} سجل`):(rec.query?'0 نتيجة':'0 سجل');
  let pager=card.querySelector('.table-pagination');const html=this.tablePager(key,rec);if(html){if(pager)pager.outerHTML=html;else card.insertAdjacentHTML('beforeend',html)}else pager?.remove();
  const table=body.closest('table');table?.removeAttribute('data-responsive-ready');this.enhanceResponsiveTables(card);return true;
},

filterTable:function(input){
  const card=input.closest('.table-card'),q=this.searchNormalize(input.value),key=card?.dataset?.lazyTable,rec=key?this._lazyTables.get(key):null;
  if(!rec||rec.kind!=='data')return UI_Tables.filterTable.call(this,input);
  rec.query=q;
  if(!q)rec.filtered=rec.rows.slice();
  else{
    if(!rec.searchIndex){rec.searchIndex=rec.rows.map(x=>this.dataTableSearchValue(rec,x));rec.searchIndexBuilding=false}
    rec.filtered=rec.rows.filter((_,i)=>rec.searchIndex[i].includes(q));
  }
  rec.page=1;return this.renderTablePage(key,card);
},

sortTable:function(th,index){
  if(th.dataset.export==='0')return;
  const card=th.closest('.table-card'),key=card?.dataset?.lazyTable,rec=key?this._lazyTables.get(key):null;
  if(!rec||rec.kind!=='data')return UI_Tables.sortTable.call(this,th,index);
  const stateKey=`${this.current}:${index}`,dir=this.sortState[stateKey]==='asc'?'desc':'asc';this.sortState[stateKey]=dir;
  for(const x of th.parentElement.children)x.removeAttribute('aria-sort');th.setAttribute('aria-sort',dir==='asc'?'ascending':'descending');
  const getter=rec.sortValues[index],value=item=>{if(typeof getter==='function'){try{return getter(item)}catch{return''}}const cells=this.tableRowCells(rec.rowRenderer(item));return cells[index]||''},cmp=(a,b)=>{const A=value(a),B=value(b),an=typeof A==='number'?A:parseFloat(S(A).replace(/[^0-9.-]/g,'')),bn=typeof B==='number'?B:parseFloat(S(B).replace(/[^0-9.-]/g,'')),v=Number.isFinite(an)&&Number.isFinite(bn)?an-bn:S(A).localeCompare(S(B),'ar',{numeric:true,sensitivity:'base'});return dir==='asc'?v:-v};
  rec.filtered.sort(cmp);if(!rec.query){rec.rows=rec.filtered.slice();rec.searchIndex=null}rec.page=1;return this.renderTablePage(key,card);
},

exportTable:function(btn){
  const card=btn.closest('.table-card'),key=card?.dataset?.lazyTable,rec=key?this._lazyTables.get(key):null;
  if(!rec||rec.kind!=='data')return UI_Tables.exportTable.call(this,btn);
  const table=card.querySelector('table'),include=[...table.tHead.rows[0].cells].map((c,i)=>c.dataset.export!=='0'?i:-1).filter(i=>i>=0),quote=v=>`"${S(v).replace(/"/g,'""').replace(/\n+/g,' ')}"`,head=include.map(i=>quote(table.tHead.rows[0].cells[i]?.innerText||'')).join(','),rows=rec.filtered.map(item=>{let cells;if(rec.exportValues){try{cells=rec.exportValues(item)||[]}catch{cells=[]}}else cells=this.tableRowCells(rec.rowRenderer(item));return include.map(i=>quote(cells[i]||'')).join(',')}),blob=new Blob(['﻿'+[head,...rows].join('\n')],{type:'text/csv;charset=utf-8'}),a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=`${document.getElementById('pageTitle').textContent}_${today()}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return true;
},
};
export { UI_DataTables };
