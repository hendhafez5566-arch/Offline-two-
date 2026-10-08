/* Store access port for the presentation layer.
   The UI needs three things from the company data store: live collections, the atomic transaction runner, and the save/audit hooks.
   It reaches them through this module so that no UI file names the DB global; the real store is injected by bootstrap (composeStoreAccessDeps).
   Every method reads the live store at call time (never a snapshot) and returns the same object references the store holds. */
import type { ERPData } from '../persistence/browser-store';
interface AtomicOptions { save?: boolean; render?: boolean; rollback?: boolean }
interface AtomicAsyncOptions extends AtomicOptions { strict?: boolean; waitForSave?: boolean }
interface SaveOptions { silentUi?: boolean; background?: boolean; [option: string]: unknown }
interface StoreAccessDeps<TData = ERPData> {
    store: { data(): TData; lastSaveError(): string; syncBlocked(): boolean; adopt(data: TData): void; clearSyncBlock(): void };
    transactions: {
        atomic<T>(label: string, work: () => T, options?: AtomicOptions): T;
        atomicAsync<T>(label: string, work: () => Promise<T> | T, options?: AtomicAsyncOptions): Promise<T>;
    };
    persistence: { save(render?: boolean, options?: SaveOptions): unknown; log(action: string, entity: string, id: string, details?: string): unknown };
}
const StoreAccess = {
    /* The whole live data object (null before the store is opened, exactly like DB.data). */
    data: <TData>(d: StoreAccessDeps<TData>) => d.store.data(),
    /* One live collection / settings object by name. */
    get: <TData, K extends keyof TData>(d: StoreAccessDeps<TData>, name: K): TData[K] => d.store.data()[name],
    lastSaveError: (d: StoreAccessDeps) => d.store.lastSaveError(),
    syncBlocked: (d: StoreAccessDeps) => d.store.syncBlocked(),
    /* Replace the live data with a fresher server copy (re-ensures structure, clears the sync-blocked flag and last save error). */
    adopt: <TData>(d: StoreAccessDeps<TData>, data: TData) => d.store.adopt(data),
    /* The pending local edit was synced or deliberately discarded: clear the blocked flag and last save error. */
    clearSyncBlock: (d: StoreAccessDeps) => d.store.clearSyncBlock(),
    atomic: <T>(d: StoreAccessDeps, label: string, work: () => T, options?: AtomicOptions): T => options === undefined ? d.transactions.atomic(label, work) : d.transactions.atomic(label, work, options),
    atomicAsync: <T>(d: StoreAccessDeps, label: string, work: () => Promise<T> | T, options?: AtomicAsyncOptions): Promise<T> => options === undefined ? d.transactions.atomicAsync(label, work) : d.transactions.atomicAsync(label, work, options),
    save: (d: StoreAccessDeps, ...args: [render?: boolean, options?: SaveOptions]) => d.persistence.save(...args),
    log: (d: StoreAccessDeps, action: string, entity: string, id: string, details?: string) => details === undefined ? d.persistence.log(action, entity, id) : d.persistence.log(action, entity, id, details),
};
export { StoreAccess };
export type { StoreAccessDeps, AtomicOptions, AtomicAsyncOptions, SaveOptions };
