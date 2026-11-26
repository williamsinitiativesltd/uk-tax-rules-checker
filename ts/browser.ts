import { calculate as allowance } from "../areas/personal_allowance/calculator.js";
import { calculate as duty } from "../areas/sdlt/calculator.js";

function input(root: HTMLElement, name: string, title: string, type: string) {
    const label = document.createElement("label");
    const field = document.createElement("input");
    field.type = type;
    field.name = name;
    label.append(title + " ", field);
    root.append(label);
    return field;
}

async function mount(root: HTMLElement) {
    const response = await fetch(root.dataset.rules!);
    if (!response.ok) throw new Error("Could not load the calculator rules.");
    const rules = await response.json();
    const personal = root.dataset.vendor === "pa";
    const heading = document.createElement("h3");
    heading.textContent = personal ? "Calculate personal allowance" : "Calculate Stamp Duty Land Tax";
    root.append(heading);
    const period = personal ? input(root, "tax_year_start", "Tax year starting in", "number")
                            : input(root, "effective_date", "Effective date", "date");
    const pounds = personal ? input(root, "adjusted_net_income_pounds", "Adjusted net income (£)", "text")
                            : input(root, "price_pounds", "Price (£)", "text");
    pounds.inputMode = "decimal";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Calculate";
    const output = document.createElement("output");
    button.addEventListener("click", () => {
        try {
            const result = personal
                ? allowance(rules, {tax_year_start: Number(period.value), adjusted_net_income_pounds: pounds.value})
                : duty(rules, {effective_date: period.value, price_pounds: pounds.value});
            const amount = "tax_pounds" in result ? result.tax_pounds : result.allowance_pounds;
            output.textContent = "£" + amount.toLocaleString("en-GB") + ". " + result.provision;
        } catch (error) {
            output.textContent = error instanceof Error ? error.message : String(error);
        }
    });
    root.append(button, output);
}

const root = document.getElementById("calculator");
if (root) mount(root).catch(() => { root.textContent = "Could not load the calculator rules."; });
