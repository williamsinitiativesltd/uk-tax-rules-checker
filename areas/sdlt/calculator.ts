import { hundredths } from "../../ts/decimal.js";

interface Version {
    from: string;
    to: string | null;
    citation: string;
    method: "slab" | "slice";
    bands: { lower: number, upper: number | null, rate: string }[];
}

interface Input {
    effective_date: string;
    price_pounds: string;
}

export function calculate(rules: { versions: Version[] }, input: Input) {
    const day = input.effective_date;
    const date = new Date(day);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== day) {
        throw new RangeError("Expected an ISO calendar date");
    }
    const matches = rules.versions.filter(v => v.from <= day && (v.to === null || day <= v.to));
    if (matches.length !== 1) throw new RangeError("Expected one SDLT rule in force on " + day);
    const [version] = matches;
    if (version.method !== "slab" && version.method !== "slice") throw new Error("Unknown SDLT method");

    const price = hundredths(input.price_pounds);
    let duty = 0n;
    for (const band of version.bands) {
        const lower = BigInt(band.lower) * 100n;
        if (price <= lower) break;
        const upper = band.upper === null ? price : BigInt(band.upper) * 100n;
        if (version.method === "slab" && price > upper) continue;
        const slice = (price < upper ? price : upper) - lower;
        const taxable = version.method === "slab" ? price : slice;
        duty += taxable * hundredths(band.rate);
    }
    return { tax_pounds: duty / 10000n, provision: version.citation };
}
