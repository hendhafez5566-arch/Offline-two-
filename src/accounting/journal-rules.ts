import { BusinessValues } from '../core/business-values';
import type { BusinessJournalLine, JournalRuleDeps } from '../application/business-contracts';
// Used by every posting path, including advanced accounting; no accounting policy change.
const JournalRules = {
    normalize(d: JournalRuleDeps, lines: BusinessJournalLine[], date: string) {
        if (!lines.length)
            throw new Error('القيد بدون أطراف');
        const norm: (BusinessJournalLine & {
            baseDebit: number;
            baseCredit: number;
        })[] = [], baseCurrency = d.baseCurrency;
        const raw: {debit:number;credit:number}[] = [];
        for (const l of lines) {
            for (const key of ['debit','credit','baseDebit','baseCredit','rate','baseAmount']) {
                if (l[key] != null && (!Number.isFinite(Number(l[key])) || Number(l[key]) < 0)) throw new Error('قيمة طرف القيد غير صحيحة');
            }
            d.validateLine(l);
            const baseOnly = !!l.baseOnly, c = BusinessValues.text(l.currency || baseCurrency).toUpperCase(), rate = BusinessValues.number(l.rate) || d.rate(c, date);
            if (!baseOnly && (!(rate > 0) || (l.rate != null && !(Number(l.rate)>0))))
                throw new Error(`لا يوجد سعر صرف صالح للعملة ${c}`);
            let dr = BusinessValues.number(l.debit), cr = BusinessValues.number(l.credit), bd = BusinessValues.number(l.baseDebit), bc = BusinessValues.number(l.baseCredit);
            if (baseOnly) {
                if (bd < 0 || bc < 0 || (bd > 0) === (bc > 0))
                    throw new Error('طرف إعادة التقييم غير صحيح');
                dr = cr = 0;
                raw.push({debit:bd,credit:bc});
                bd = d.round(bd, baseCurrency);
                bc = d.round(bc, baseCurrency);
            }
            else {
                if (dr < 0 || cr < 0 || (!dr && !cr) || dr && cr)
                    throw new Error('طرف قيد غير صحيح');
                raw.push({debit:dr?(l.baseAmount??dr*rate):0,credit:cr?(l.baseAmount??cr*rate):0});
                bd = d.round(dr?(l.baseAmount??dr*rate):0, baseCurrency);
                bc = d.round(cr?(l.baseAmount??cr*rate):0, baseCurrency);
            }
            norm.push({
                ...l, currency: c, debit: dr, credit: cr, rate: baseOnly ? 0 : rate, baseDebit: bd, baseCredit: bc, baseOnly
            });
        }
        // Reconcile conversion rounding only when the unrounded journal balances.
        // A genuine one-cent difference must never be silently accepted.
        const rawDebit=raw.reduce((s,l)=>s+l.debit,0), rawCredit=raw.reduce((s,l)=>s+l.credit,0);
        if (Math.abs(rawDebit-rawCredit)>Math.max(1e-7, Math.max(rawDebit,rawCredit)*1e-12))
            throw new Error(`القيد غير متزن: ${d.format(rawDebit)} / ${d.format(rawCredit)}`);
        const target=d.round(rawDebit,baseCurrency);
        for (const [field,side] of [['baseDebit','debit'],['baseCredit','credit']] as const) {
            let delta=d.round(target-norm.reduce((s,l)=>s+l[field],0),baseCurrency);
            const candidates=norm.map((l,i)=>({i,error:raw[i][side]-l[field]})).filter(x=>raw[x.i][side]>0).sort((a,b)=>delta>0?b.error-a.error:a.error-b.error);
            if (delta && candidates.length) {
                const unit=10**-(([0,1,2,3,4,5,6,7].find(n=>d.round(10**-n,baseCurrency)===0) ?? 7)-1);
                // distribute residual by largest rounding error, preserving the total.
                for(let k=0;Math.abs(delta)>1e-9;k++) {
                    const l=norm[candidates[k%candidates.length].i],change=Math.sign(delta)*Math.min(Math.abs(delta),Number.isFinite(unit)?unit:Math.abs(delta));
                    l[field]=d.round(l[field]+change,baseCurrency);delta=d.round(delta-change,baseCurrency);
                }
            }
        }
        for(const l of norm)if(!l.baseOnly)l.baseAmount=l.baseDebit||l.baseCredit;
        return norm;
    }, reversalLines(lines: BusinessJournalLine[] = []) {
        return lines.map(l => {
            const x = {
                ...l
            };
            delete x.debit;
            delete x.credit;
            delete x.baseDebit;
            delete x.baseCredit;
            if (l.baseOnly)
                return {
                    ...x, baseDebit: l.baseCredit, baseCredit: l.baseDebit, currency: l.currency, baseOnly: true
                };
            return {
                ...x, debit: l.credit, credit: l.debit, currency: l.currency, rate:l.rate,baseAmount:Number(l.baseDebit||l.baseCredit),baseOnly: false
            };
        });
    }
};
export { JournalRules };
