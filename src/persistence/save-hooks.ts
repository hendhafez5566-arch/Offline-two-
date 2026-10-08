/* Pre-save hook registry: lets the store run a domain step before persisting without importing or naming the domain layer.
   Leaf module (no imports). The owner of the step registers it when it is defined; until then saving behaves exactly as if no step existed. */
let beforeSave: (() => void) | null = null;
const SaveHooks = {
    registerBeforeSave(hook: () => void) { beforeSave = hook; },
    runBeforeSave() { if (beforeSave) beforeSave(); }
};
export { SaveHooks };
