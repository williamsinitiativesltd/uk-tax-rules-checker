import { readFileSync } from "node:fs";

const area = process.argv[2];
if (!["sdlt", "personal_allowance"].includes(area)) throw new Error("Expected a calculator area");
const { calculate } = await import(`../areas/${area}/calculator.js`);
const rules = JSON.parse(readFileSync(`areas/${area}/rules.json`, "utf8"));
const input = JSON.parse(readFileSync(0, "utf8"), (key, value, context) => {
    if (key !== "price_pounds" && key !== "adjusted_net_income_pounds") return value;
    if (typeof value !== "number") throw new TypeError("Expected a JSON number in pounds");
    // The token still has every digit even when the parsed Number has lost pence.
    return context.source;
});
const { provision, ...reply } = calculate(rules, input);
console.log(JSON.stringify(reply, (_, value) => typeof value === "bigint" ? JSON.rawJSON(String(value)) : value));
