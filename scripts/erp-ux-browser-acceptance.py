"""ERP replacement acceptance. Isolated browser data; never touches company data."""
import asyncio, functools, http.server, json, os, pathlib, threading
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
async def main():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT/'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'), headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = await browser.new_page(viewport={'width':1440,'height':960})
            errors=[]
            page.on('pageerror', lambda e: errors.append(str(e)))
            await page.goto(f'http://127.0.0.1:{server.server_port}/', wait_until='networkidle')
            await page.evaluate('''()=>{DB.data=deep(Seed);DB.data.meta.setupComplete=true;DB.ensure();Auth.user={id:'ux-review',name:'أحمد محمد',role:'admin',active:true,onboardingSeen:true,permissions:{all:true},allowedBranchIds:[]};DB.data.users=[Auth.user];DB.data.company.name='ELHAFEZ TOURISM';document.getElementById('login').classList.add('hidden');document.getElementById('app').classList.remove('hidden');UI.init()}''')
            result=await page.evaluate('''()=>{
                const check=(v,m)=>{if(!v)throw Error(m)}, routes=[];
                for(const ws of UI.workspaces()){
                    UI.openWorkspace(ws.id);check(document.querySelectorAll('#nav .main-section-nav>.nav-btn').length===8,'sidebar sections');
                    for(const route of ws.pages){if(!Auth.can(route))continue;UI.openPage(route);check(UI.current===route,'route denied: '+route);check(!!document.querySelector('#pages .page'),'missing '+route);routes.push(route)}
                }
                check(UI.workspaceForPage('umrah-contracts').id==='procurement','contracts owner');
                check(UI.workspaceForPage('umrah-procurement').id==='procurement','inventory owner');
                UI.openPage('customers');const host=document.getElementById('pages');
                host.innerHTML=UI.table(['الاسم','القيمة','الإجراءات'],Array.from({length:31},(_,i)=>`<tr><td>عميل ${i}</td><td>${i}</td><td>فتح</td></tr>`));
                const card=host.querySelector('.table-card'), table=card.querySelector('table'), input=card.querySelector('[data-ui-table-column="1"]');
                input.checked=false;input.dispatchEvent(new Event('change',{bubbles:true}));check(table.rows[0].cells[1].hidden,'column not hidden');
                UI.pageTable(card.dataset.lazyTable,1,card.querySelector('[data-ui-page-dir="1"]'));check(table.rows[1].cells[1].hidden,'page lost column selection');
                const before=table.rows[1].cells[0].textContent;check(before==='عميل 25','page next');
                UI.restoreTableColumns(table);check(!table.rows[0].cells[2].hidden,'actions hidden');
                const admin=Auth.user;Auth.user={id:'ux-sales',role:'sales',active:true,permissions:{...Object.fromEntries([...UI.workspaces().flatMap(w=>w.pages),'journal','reports','settings'].map(p=>[p,{view:false}])),customers:{view:true},'umrah-bookings':{view:true}},customPermissions:true};
                check(!Auth.can('journals','approve'),'finance privilege');check(!UI.workspaces().some(w=>w.id==='finance'),'finance visible');
                UI.openPage('customers');UI.openPage('journals');check(UI.current==='customers','unauthorized navigation');Auth.user=admin;UI.openPage('umrah-bookings');document.getElementById('toast').classList.remove('show');
                return {routes:routes.length,columnPersistence:true,pageNavigation:true,procurementOwnership:true,roleIsolation:true};
            }''')
            await page.wait_for_timeout(300)
            if os.environ.get('UX_SCREENSHOT_DIR'):
                dest=pathlib.Path(os.environ['UX_SCREENSHOT_DIR']);dest.mkdir(parents=True,exist_ok=True)
                await page.screenshot(path=str(dest/'desktop.png'),full_page=True)
            await page.set_viewport_size({'width':390,'height':844})
            await page.evaluate('UI.setSidebarOpen(true)')
            await page.wait_for_timeout(300)
            assert await page.evaluate('''()=>{const b=document.querySelector('#nav .nav-btn'),r=b.getBoundingClientRect();return b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}'''), 'mobile backdrop blocks sidebar'
            await page.evaluate('UI.setSidebarOpen(false)')
            if os.environ.get('UX_SCREENSHOT_DIR'):
                await page.screenshot(path=str(dest/'mobile.png'),full_page=True)
            assert not errors,errors
            print(json.dumps({'ok':True,**result,'mobileSidebarAccessible':True,'pageErrors':errors},ensure_ascii=False,indent=2))
            await browser.close()
    finally: server.shutdown()
asyncio.run(main())
