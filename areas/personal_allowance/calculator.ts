import { hundredths } from "../../ts/decimal.js";

interface Rules {
    years: Record<string, { amount: number, citation: string }>;
    taper: { first_year: number, income_limit: number, divisor: number, citation: string };
}

interface Input {
    tax_year_start: number;
    adjusted_net_income_pounds: string;
}

export function calculate(rules: Rules, input: Input) {
    const year = input.tax_year_start;
    const annual = rules.years[year];
    if (!Number.isInteger(year) || !annual) throw new RangeError("No allowance for this tax year");
    const income = hundredths(input.adjusted_net_income_pounds);
    const taper = rules.taper;
    const excess = income - BigInt(taper.income_limit) * 100n;
    let allowance = BigInt(annual.amount);
    let provision = annual.citation;
    if (year >= taper.first_year && excess > 0n) {
        allowance -= excess / (BigInt(taper.divisor) * 100n);
        provision += "; " + taper.citation;
    }
    return { allowance_pounds: allowance > 0n ? allowance : 0n, provision };
}
