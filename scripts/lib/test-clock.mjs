/** Test-only clock: fixtures remain deterministic while production date guards stay enabled. */
export function freezeClock(iso) {
 const OriginalDate=globalThis.Date;
 const instant=OriginalDate.parse(iso.includes('T')?iso:iso+'T12:00:00Z');
 if(!Number.isFinite(instant))throw new Error('Invalid fixture clock');
 class FixtureDate extends OriginalDate {
  constructor(...args){super(...(args.length?args:[instant]));}
  static now(){return instant;}
 }
 globalThis.Date=FixtureDate;
 return ()=>{globalThis.Date=OriginalDate;};
}
