import { StoreAccess } from '../application/store-access';
import { composeStoreAccessDeps } from '../core/late-bindings';
import type { ERPData } from '../persistence/browser-store';
import type { AtomicAsyncOptions, AtomicOptions, SaveOptions } from '../application/store-access';
/* Presentation-side handle on the company data store. Same live data and the same transaction/save/audit behaviour the UI had through the DB global;
   the dependency is injected by bootstrap, so UI code never names DB. `Store.data()` is DB.data; `Store.get('x')` is DB.data.x. */
const Store = {
    data: () => StoreAccess.data(composeStoreAccessDeps()),
    get: <K extends keyof ERPData>(name: K): ERPData[K] => StoreAccess.get(composeStoreAccessDeps(), name),
    get lastSaveError(): string { return StoreAccess.lastSaveError(composeStoreAccessDeps()); },
    atomic: <T>(label: string, work: () => T, options?: AtomicOptions): T => StoreAccess.atomic(composeStoreAccessDeps(), label, work, options),
    atomicAsync: <T>(label: string, work: () => Promise<T> | T, options?: AtomicAsyncOptions): Promise<T> => StoreAccess.atomicAsync(composeStoreAccessDeps(), label, work, options),
    save: (render?: boolean, options?: SaveOptions) => StoreAccess.save(composeStoreAccessDeps(), render, options),
    log: (action: string, entity: string, id: string, details?: string) => StoreAccess.log(composeStoreAccessDeps(), action, entity, id, details),
};
export { Store };
