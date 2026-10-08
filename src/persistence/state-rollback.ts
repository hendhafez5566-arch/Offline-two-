/** Restore a transaction snapshot while keeping references to existing records valid. */
export function restoreState(target: any, snapshot: any): any {
  if (Array.isArray(snapshot)) {
    if (!Array.isArray(target)) return structuredClone(snapshot);
    const records = new Map(target.filter(x => x && typeof x === 'object' && x.id).map(x => [x.id, x]));
    const values = snapshot.map((value, index) => restoreState(value?.id ? records.get(value.id) : target[index], value));
    target.splice(0, target.length, ...values);
    return target;
  }
  if (snapshot && typeof snapshot === 'object') {
    if (!target || typeof target !== 'object' || Array.isArray(target)) return structuredClone(snapshot);
    for (const key of Object.keys(target)) if (!(key in snapshot)) delete target[key];
    for (const [key, value] of Object.entries(snapshot)) target[key] = restoreState(target[key], value);
    return target;
  }
  return snapshot;
}
