export const UIDocument: any = document;

// Offline font catalog: selected families ship with the application and their SIL licenses.
export const SystemFontCatalog: any={
 default:{label:'الافتراضي',stack:'Tahoma,"Noto Sans Arabic","Segoe UI",Arial,sans-serif',href:''},
 cairo:{label:'Cairo',stack:'"Cairo",Tahoma,"Noto Sans Arabic",Arial,sans-serif',href:'./fonts/cairo.css'},
 tajawal:{label:'Tajawal',stack:'"Tajawal",Tahoma,"Noto Sans Arabic",Arial,sans-serif',href:'./fonts/tajawal.css'},
 noto:{label:'Noto Sans Arabic',stack:'"Noto Sans Arabic",Tahoma,Arial,sans-serif',href:'./fonts/noto.css'},
 plex:{label:'IBM Plex Arabic',stack:'"IBM Plex Sans Arabic","Noto Sans Arabic",Tahoma,Arial,sans-serif',href:'./fonts/plex.css'},
 kufi:{label:'Noto Kufi Arabic',stack:'"Noto Kufi Arabic","Noto Sans Arabic",Tahoma,Arial,sans-serif',href:'./fonts/kufi.css'}
};

export const systemFontEntry=value=>SystemFontCatalog[value]||SystemFontCatalog.default;

export const ensureSystemFontAsset=value=>{const entry=systemFontEntry(value),id='erpSystemFontCss';let link=UIDocument.getElementById(id);if(!entry.href){link?.remove();return entry}if(!link){link=UIDocument.createElement('link');link.id=id;link.rel='stylesheet';UIDocument.head.appendChild(link)}if(link.getAttribute('href')!==entry.href)link.setAttribute('href',entry.href);return entry};
