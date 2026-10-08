"""Focused UI durability acceptance with explicitly injected storage faults; no screenshots.
The original v32.5.70 bundle can be supplied via BASELINE_APP for the stale-window reproduction.
"""
import tempfile, shutil
from pathlib import Path
exec((Path(__file__).with_name('f11-f18-storage-ui-acceptance.py')).read_text().split('import tempfile\n')[0])
records=[]
def record(name,facts):
 records.append({'case':name,'status':'PASS','facts':facts});print(name,'PASS',flush=True)
 (OUT/('baseline-durability-recovery-results.json' if os.environ.get('BASELINE_APP') else 'durability-recovery-results.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2))
def enter_existing(page):
 page.goto(URL);page.wait_for_function('DB.data?.meta.setupComplete');page.wait_for_timeout(300)
 if page.evaluate('Auth.user?.username==="qa"&&!document.getElementById("app").classList.contains("hidden")'):return
 page.locator('#loginForm [name=username]').fill('qa');page.locator('#loginForm [name=password]').fill('QATest123!');page.locator('#loginForm button[type=submit]').click(no_wait_after=True)
 page.wait_for_function('Auth.user?.username==="qa"&&!document.getElementById("app").classList.contains("hidden")')
 if not os.environ.get('BASELINE_APP'):settled(page)
def add_customer_ui(page,name):
 nav(page,'customers');page.locator('[data-form-open=customer]:visible').first.click();page.locator('#modalBody [name=name]').fill(name);page.locator('#modalForm button[type=submit]').click(no_wait_after=True)
def add_file_ui(page,name,content):
 nav(page,'documents');page.locator('[data-form-open=attachment]:visible').first.click();page.locator('#modalBody [name=entityId]').fill(page.evaluate('DB.data.customers[0].no'));page.locator('#modalBody [name=file]').set_input_files({'name':name,'mimeType':'text/plain','buffer':content});submit(page);page.wait_for_timeout(300) if os.environ.get('BASELINE_APP') else settled(page);return raw(page)['attachments'][0]
def reverse_ack_ui(page):
 ids=page.evaluate("""async()=>{let ids;await DB.atomicAsync('ack fixture',()=>{const a=Transactions.createTreasury({name:'ACK Source',currency:'EGP',type:'cash',opening:1000,date:today(),silent:true}),b=Transactions.createTreasury({name:'ACK Target',currency:'EGP',type:'cash',opening:0,date:today(),silent:true});ids={a:a.id,b:b.id}});return ids}""")
 tr=transfer(page,ids['a'],ids['b'],'5')
 page.evaluate("""()=>{const notice=document.getElementById('toast');if(notice){notice.textContent='';notice.className='toast'}const put=DataStore.put.bind(DataStore);DataStore.put=(...args)=>new Promise((resolve,reject)=>{window.qaDelayedSave=true;window.qaResume=()=>put(...args).then(resolve,reject)})}""")
 nav(page,'treasury');page.locator('[data-treasury-tab=transfers]').click();reveal_click(page,f'[data-clean-action=reverseTransfer][data-clean-id="{tr["id"]}"]');page.locator('#modalBody [name=reason]').fill('Delayed storage acknowledgement');page.locator('#modalForm button[type=submit]').click(no_wait_after=True);page.wait_for_function('window.qaDelayedSave===true');page.wait_for_timeout(100)
 disk=page.evaluate('async()=>await DataStore.localGet()');check(next(t for t in disk['transfers'] if t['id']==tr['id'])['status']=='posted','injected write was not held')
 acknowledged='تم عكس التحويل' in page.locator('body').inner_text()
 if os.environ.get('BASELINE_APP'):check(acknowledged,'original false acknowledgement not reproduced');record('F15 original success before commit',{'uiSuccessBeforeStorage':True,'diskStillPosted':True})
 else:check(not acknowledged and page.locator('#modal').evaluate('el=>el.classList.contains("show")'),'success before commit');record('F15 reversal UI waits for commit',{'noPrematureSuccess':True,'formRemainsPending':True,'diskStillPosted':True})
 page.evaluate('()=>window.qaResume()');page.wait_for_function('!document.getElementById("modal").classList.contains("show")');settled(page)
 check(next(t for t in page.evaluate('async()=>await DataStore.localGet()')['transfers'] if t['id']==tr['id'])['status']=='void','released write not durable')
 # Restore the real adapter; the injected gate belongs to this case only.
 page.reload();enter_existing(page)
def restore_ui(page,pkg,interruption=0):
 path=Path(tempfile.mktemp(suffix='.erpbackup'));path.write_text(json.dumps(pkg,ensure_ascii=False))
 nav(page,'backup-center');page.locator('#backupRestoreFile').set_input_files(str(path));page.locator('#restoreSafetyBackup').wait_for();page.locator('#restoreSafetyBackup').uncheck()
 if interruption:
  page.evaluate('''(target)=>{const put=AttachmentStore.localPut.bind(AttachmentStore);let n=0;AttachmentStore.localPut=async(...a)=>{if(++n===target){window.qaInterrupted=true;return new Promise(()=>{})}return put(...a)}}''',interruption)
 page.locator('#modalForm button[type=submit]').click(no_wait_after=True)
 if interruption:page.wait_for_function('window.qaInterrupted===true')
 else:page.wait_for_function('DB.data?.meta.restoredFrom==="backup"')
 path.unlink()
with sync_playwright() as p:
 profile=tempfile.mkdtemp(prefix='elhafez-recovery-')
 def launch():return p.chromium.launch_persistent_context(profile,executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,service_workers='block',args=['--no-sandbox','--disable-dev-shm-usage'])
 ctx=launch();page=ctx.new_page();page.set_default_timeout(20000);page.on('dialog',lambda d:d.accept('QA'))
 try:
  if os.environ.get('BASELINE_APP'):
   settled=lambda page:page.wait_for_timeout(250)
   baseline=Path(os.environ['BASELINE_APP']).read_text();ctx.route('**/app.js*',lambda route:route.fulfill(body=baseline,content_type='application/javascript'))
   # Seed shares credentials but original build has no saveQueue/pendingSaves.
   seed_src=seed.__code__
   page.goto(URL);page.wait_for_function('DB.data');page.wait_for_timeout(500)
   page.evaluate('''async()=>{DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();const u={id:'qa-admin',name:'QA',username:'qa',role:'admin',active:true,onboardingSeen:true,permissions:{all:true}};await Security.setPassword(u,'QATest123!');DB.data.users=[u];Auth.user=u;await Commercial.afterInit();await DB.save(false);Auth.enter()}''')
  else:seed(page)
  second=ctx.new_page();enter_existing(second)
  add_customer_ui(second,'COMMITTED OTHER WINDOW');second.wait_for_timeout(400)
  if not os.environ.get('BASELINE_APP'):settled(second);second.wait_for_function('!document.getElementById("modal").classList.contains("show")')
  add_customer_ui(page,'STALE WINDOW WRITE');page.wait_for_timeout(600)
  disk=page.evaluate('async()=>await DataStore.localGet()')
  if os.environ.get('BASELINE_APP'):
   check(not any(c['name']=='COMMITTED OTHER WINDOW' for c in disk['customers']),'original stale window did not reproduce loss');record('F15 original stale-window loss',{'newerRecordLost':True});second.close();reverse_ack_ui(page)
   a=add_file_ui(page,'recovery-a.txt',b'Original attachment A');b=add_file_ui(page,'recovery-b.txt',b'Original attachment B');pkg=page.evaluate('async()=>await Backup.build()')
   restore_ui(page,pkg,1);ctx.close();ctx=launch();ctx.route('**/app.js*',lambda route:route.fulfill(body=baseline,content_type='application/javascript'));page=ctx.new_page();page.set_default_timeout(20000);page.on('dialog',lambda d:d.accept('QA'));enter_existing(page)
   missing=page.evaluate('async()=>await Promise.all(DB.data.attachments.map(async(a)=>({id:a.id,exists:!!await AttachmentStore.get(a.id)})))')
   check(len(missing)==2 and all(not x['exists'] for x in missing),'original interrupted restore did not reproduce metadata without bytes');record('F17 original interrupted restore loses attachment bytes',{'metadataRecords':len(missing),'missingBlobCount':len(missing),'actualBrowserClosed':True});sys.exit(0)
  check(any(c['name']=='COMMITTED OTHER WINDOW' for c in disk['customers']),'newer durable customer lost');check(not any(c['name']=='STALE WINDOW WRITE' for c in disk['customers']),'stale save accepted');check(page.evaluate('DB.syncBlocked&&!!DB.lastSaveError'),'no explicit blocking/error');check(page.locator('#modal').evaluate('el=>el.classList.contains("show")'),'failed form closed');check(not any(c['name']=='STALE WINDOW WRITE' for c in raw(page)['customers']),'failed candidate did not rollback');record('F15 stale-window rejected from UI',{'newerRecordPreserved':True,'failedFormOpen':True,'rollback':True,'explicitErrorAndBlock':True})
  second.close();page.reload();enter_existing(page);reverse_ack_ui(page)
  a=add_file_ui(page,'recovery-a.txt',b'Original attachment A');b=add_file_ui(page,'recovery-b.txt',b'Original attachment B')
  pkg=page.evaluate('async()=>await Backup.build()');expected=pkg['data']['journals']
  # Deletion rollback must preserve the physical bytes as well as metadata.
  facts=page.evaluate('''async(id)=>{const before=JSON.stringify(DB.data),put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,k){if(this.name==='state'&&k==='main')throw new DOMException('injected quota','QuotaExceededError');return put.call(this,v,k)};let rejected=false;try{await DB.atomicAsync('attachment delete failure',()=>Attachments.remove(id),{strict:true})}catch(_){rejected=true}finally{IDBObjectStore.prototype.put=put}const out={rejected,metadataRollback:JSON.stringify(DB.data)===before,bytes:await(await AttachmentStore.get(id)).text()};await DB.save(false);return out}''',a['id'])
  check(facts=={'rejected':True,'metadataRollback':True,'bytes':'Original attachment A'},'delete failure lost bytes');record('F17 failed deletion preserves metadata and bytes',facts)
  # UI repair: remove bytes explicitly to reproduce the reported metadata-only state.
  page.evaluate('async(id)=>await AttachmentStore.localRemove(id)',a['id'])
  failure=page.evaluate('async()=>{try{await Backup.build();return false}catch(e){return e.message}}');check(bool(failure),'incomplete backup accepted')
  nav(page,'documents');reveal_click(page,f'[data-form-open=attachmentRecovery][data-edit-id="{a["id"]}"]');page.locator('#modalBody [name=file]').set_input_files({'name':'recovery-a.txt','mimeType':'text/plain','buffer':b'Wrong replacement AAAA'});page.locator('#modalForm button[type=submit]').click(no_wait_after=True);page.wait_for_timeout(150);check(not page.evaluate('async(id)=>!!(await AttachmentStore.get(id))',a['id']),'wrong recovery bytes accepted')
  page.locator('#modalBody [name=file]').set_input_files({'name':'recovery-a.txt','mimeType':'text/plain','buffer':b'Original attachment A'});submit(page);settled(page)
  restored=raw(page)['attachments'];recovered=next(x for x in restored if x['id']==a['id']);check(recovered['createdAt']==a['createdAt'] and recovered['version']==a['version'],'attachment identity/history changed');check(page.evaluate('async(id)=>(await AttachmentStore.get(id)).text()',a['id'])=='Original attachment A','UI recovery bytes');record('F17 metadata-only fault and original-file recovery UI',{'backupRejectedMissingBytes':str(failure),'wrongBytesRejected':True,'originalBytesRestored':True,'identityAndHistoryPreserved':True})
  pkg=page.evaluate('async()=>await Backup.build()');expected=pkg['data']['journals']
  # Abort restore write once; the journal compensates before notifying a failure.
  facts=page.evaluate('''async(pkg)=>{const before=JSON.stringify(DB.data),old=AttachmentStore.localPut.bind(AttachmentStore);let n=0;AttachmentStore.localPut=async(...args)=>++n===2?false:old(...args);let rejected=false;try{await Backup.restorePackage(pkg)}catch(_){rejected=true}finally{AttachmentStore.localPut=old}const db=await DataStore.open(),intent=await new Promise((res,rej)=>{const r=db.transaction('state').objectStore('state').get('restore-intent');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});return{rejected,unchanged:JSON.stringify(DB.data)===before,disk:JSON.stringify(await DataStore.localGet())===before,intentCleared:!intent,bytes:await Promise.all(DB.data.attachments.map(async(a)=>(await AttachmentStore.get(a.id)).text()))}}''',pkg)
  check(facts['rejected'] and facts['unchanged'] and facts['disk'] and facts['intentCleared'],'restore failure rollback');check(set(facts['bytes'])=={'Original attachment A','Original attachment B'},'rollback bytes mismatch');record('F17 restore-write failure compensates both stores',facts)
  for target in [1,2]:
   add_customer_ui(page,'AFTER BACKUP '+str(target));page.wait_for_function('!document.getElementById("modal").classList.contains("show")');settled(page)
   restore_ui(page,pkg,target);check(page.evaluate('localStorage.getItem(APP.storage+"_restorePending")==="1"'),'missing recovery marker')
   ctx.close();ctx=launch();page=ctx.new_page();page.set_default_timeout(20000);page.on('dialog',lambda d:d.accept('QA'));enter_existing(page)
   after=raw(page);check(after['journals']==expected,'raw journal mismatch after interrupted restore');check(not any(c['name'].startswith('AFTER BACKUP') for c in after['customers']),'candidate restore not replayed');check(page.evaluate('async()=>await Promise.all(DB.data.attachments.map(async(a)=>(await AttachmentStore.get(a.id)).text()))')==['Original attachment B','Original attachment A'],'attachment bytes mismatch after replay');check(not page.evaluate('localStorage.getItem(APP.storage+"_restorePending")'),'recovery marker not cleared');record('F17 interrupted restore before file '+str(target),{'actualBrowserClosed':True,'journalEqual':True,'bytesEqual':True,'candidateRecovered':True})
  bad=json.loads(json.dumps(pkg));bad['attachments']=[];bad['blobs']=[];bad.pop('checksum',None)
  check(page.evaluate('async(pkg)=>{try{await Backup.verifyPackage(pkg);return false}catch(_){return true}}',bad),'metadata-only imported package accepted');record('F17 incomplete imported package rejected',{'metadataReferencesRequireManifest':True})
 finally:
  ctx.close();shutil.rmtree(profile,ignore_errors=True);server.shutdown()
