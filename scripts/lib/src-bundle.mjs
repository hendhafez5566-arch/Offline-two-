// Builds the CURRENT src/ (not the possibly stale dist/app.js) into one classic script string for VM-based smokes.
// 1) esbuild with the same settings as scripts/bundle-app.mjs when it is installed (production fidelity);
// 2) otherwise a minimal TypeScript->CommonJS fallback (test-only; same module order, live bindings via property access).
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
export async function buildAppCode() {
  try {
    const { build } = await import('esbuild');
    const r = await build({ absWorkingDir: root, entryPoints: ['src/main.ts'], write: false, bundle: true, format: 'iife', target: 'es2020', platform: 'browser', charset: 'utf8', minify: false, keepNames: true, legalComments: 'none', sourcemap: false, logLevel: 'silent', tsconfig: 'tsconfig.json' });
    return { code: r.outputFiles[0].text, engine: 'esbuild' };
  } catch (e) {
    if (e && e.code !== 'ERR_MODULE_NOT_FOUND' && !/Cannot find (package|module)/.test(String(e.message))) throw e;
  }
  const mods = {};
  const resolveMod = (from, spec) => {
    const base = path.resolve(path.dirname(from), spec);
    for (const c of [base + '.ts', path.join(base, 'index.ts'), base]) if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
    throw new Error('cannot resolve ' + spec + ' from ' + from);
  };
  const load = (file) => {
    if (mods[file]) return;
    const src = fs.readFileSync(file, 'utf8');
    const out = ts.transpileModule(src, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, removeComments: true, esModuleInterop: false }, fileName: file }).outputText;
    mods[file] = { out, deps: {} };
    for (const m of out.matchAll(/require\("(\.[^"]+)"\)/g)) { const d = resolveMod(file, m[1]); mods[file].deps[m[1]] = d; load(d); }
  };
  const entry = path.join(root, 'src/main.ts');
  load(entry);
  let code = '(function(){var __defs={},__cache={};\n';
  for (const [f, m] of Object.entries(mods)) code += `__defs[${JSON.stringify(f)}]=function(require,exports,module){${m.out}\n};\n__defs[${JSON.stringify(f)}].deps=${JSON.stringify(m.deps)};\n`;
  code += `function __req(f){if(__cache[f])return __cache[f].exports;var m=__cache[f]={exports:{}};var d=__defs[f].deps;__defs[f](function(s){return __req(d[s])},m.exports,m);return m.exports}\n__req(${JSON.stringify(entry)});})();`;
  return { code, engine: 'ts-cjs-fallback' };
}
