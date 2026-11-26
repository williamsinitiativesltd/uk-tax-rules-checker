// Prices and rates arrive as decimal text so no binary float can move a band edge.
export function hundredths(text: string): bigint {
    const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(text);
    if (!match) throw new RangeError("Expected a decimal amount");
    const [, sign, whole, fraction = "", exponent = "0"] = match;
    const digits = whole + fraction;
    const value = BigInt(digits);
    if (value === 0n) return 0n;
    if (sign) throw new RangeError("Expected a non-negative amount");

    const shift = BigInt(exponent) + 2n - BigInt(fraction.length);
    if (shift >= 0n) return value * 10n ** shift;
    if (-shift > digits.length || value % (10n ** -shift) !== 0n) {
        throw new RangeError("Expected a whole number of hundredths");
    }
    return value / (10n ** -shift);
}
