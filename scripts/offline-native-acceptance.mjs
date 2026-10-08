/** Offline edition parity and shared Android security/printing contract. Remote resolver is not part of this edition. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
const cfg=JSON.parse(read('capacitor.config.json')),pkg=JSON.parse(read('package.json'));
const runtime=read('src/core/runtime.ts'),mobile=read('src/mobile.ts'),store=read('src/persistence/server-store.ts'),pwa=read('src/pwa.ts')+read('src/platform/pwa-registration.ts')+read('src/platform/browser-platform.ts'),gradle=read('android/app/build.gradle'),manifest=read('android/app/src/main/AndroidManifest.xml'),activity=read('android/app/src/main/java/com/elhafez/tourism/erp/customer/MainActivity.java'),printing=read('src/reports/printing.ts');
const checks=[];function check(name,value){assert(value,name);checks.push(name)}
check('Offline build uses the offline application ID',cfg.appId==='com.elhafez.tourism.erp.offline'&&gradle.includes("?: 'com.elhafez.tourism.erp.offline'"));
check('Offline build uses the common compiled application',runtime.includes('offlineEdition:true')&&cfg.webDir==='dist'&&!cfg.server.url);
check('Offline build retains the original company storage',runtime.includes("storage:'erp_professional_suite_v32_2_commercial_offline'")&&runtime.includes("dataDb:'erp_professional_suite_v32_2_commercial_offline_data'"));
check('Release versions match',JSON.parse(read('server/package.json')).version===pkg.version&&runtime.includes(`version:'${pkg.version}'`)&&gradle.includes(`versionName "${pkg.version}"`)&&gradle.includes(`versionCode ${pkg.version.replaceAll('.','')}`)&&mobile.includes(`X-ERP-Mobile-Version','${pkg.version}'`));
for(const asset of ['index.html','app.js','styles.css','sw.js','manifest.webmanifest']){
 const sha=p=>createHash('sha256').update(fs.readFileSync(new URL('../'+p,import.meta.url))).digest('hex');
 check('Android/web identical asset '+asset,sha('dist/'+asset)===sha('android/app/src/main/assets/public/'+asset));
}
check('No cleartext traffic or mixed content',cfg.server.cleartext===false&&cfg.android.allowMixedContent===false&&manifest.includes('android:usesCleartextTraffic="false"'));
check('Production WebView debugging is disabled',cfg.android.webContentsDebuggingEnabled===false);
check('Application backups cannot leak local accounting data',manifest.includes('android:allowBackup="false"'));
check('Native Internet permission remains present',manifest.includes('android.permission.INTERNET'));
check('System Back and lifecycle bridge remain present',activity.includes('erp:native-back')&&activity.includes('erp:native-state')&&mobile.includes("window.addEventListener('erp:native-back'"));
check('Print and PDF sharing bridge remain present',activity.includes('PrintManager')&&activity.includes('printHtml')&&activity.includes('shareHtmlA4ToWhatsApp(String html')&&activity.includes('FileProvider.getUriForFile')&&activity.includes('application/pdf')&&printing.includes('native?.printHtml')&&printing.includes('native.shareHtmlA4ToWhatsApp(p.html,p.fileName,p.orientation,phone)'));
check('Canonical PDF output validates rendered file before use',activity.includes('file.length() <= 0')&&activity.includes('postVisualStateCallback')&&activity.includes('getOrCreateCanonicalPdf(')&&activity.includes('android.print.PdfPrint.write('));
check('Native session stays in HttpOnly cookies',mobile.includes("credentials:'include'")&&!mobile.includes('mobileSessionToken')&&!mobile.includes('erp_native_session_v1'));
check('Native shell disables stale service workers',pwa.includes('NativeShell?.isNative?.() === true')&&/if\s*\(port.native\(\)\)\s*return/.test(pwa));
check('Pending edits/conflicts remain protected during refresh',mobile.includes('dirtyFormOpen()')&&mobile.includes('ServerStore.lastConflict||StoreAccess.syncBlocked(composeStoreAccessDeps())')&&mobile.includes('ServerStore.flushPending()'));
check('Android CORS and sliding session contract remain present',read('server/src/context.ts').includes('https://localhost')&&read('server/src/context.ts').includes('MOBILE_SESSION_HOURS||720')&&read('server/src/session.ts').includes('sessionTtlHours'));
check('Offline mode cannot require a remote server',store.includes('APP.offlineEdition')&&store.includes('remoteRequired'));
console.log(JSON.stringify({ok:true,edition:'offline',checks:checks.length,remoteCustomerResolver:'not part of offline edition'},null,2));
