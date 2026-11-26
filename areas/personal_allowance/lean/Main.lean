import Lean.Data.Json
import PersonalAllowance

open Lean

def answer (input : Json) : Except String Json := do
  let year ← input.getObjValAs? Nat "tax_year_start"
  let income ← input.getObjValAs? Nat "adjusted_net_income_pounds"
  if year > 2030 then throw "year outside the allowance model"
  let some amount := PersonalAllowance.allowanceFor year (100 * income)
    | throw "year outside the allowance model"
  return Json.mkObj [("allowance_pounds", toJson amount)]

def main : IO Unit := do
  let stdin ← IO.getStdin
  let input ← IO.ofExcept (Json.parse (← stdin.readToEnd))
  IO.println (← IO.ofExcept (answer input)).compress
