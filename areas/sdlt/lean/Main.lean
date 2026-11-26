import Lean.Data.Json
import Sdlt

open Lean

def dateNumber (date : String) : Except String Nat := do
  let [year, month, day] := date.splitOn "-" | throw "expected YYYY-MM-DD"
  unless year.length == 4 && month.length == 2 && day.length == 2 do
    throw "expected YYYY-MM-DD"
  let some n := (year ++ month ++ day).toNat? | throw "expected YYYY-MM-DD"
  return n

def pricePence (price : Json) : Except String Nat := do
  let .num n := price | throw "expected a price in pounds"
  let scaled := n.mantissa.toNat * 100
  let divisor := 10 ^ n.exponent
  if n.mantissa < 0 || scaled % divisor != 0 then
    throw "expected a non-negative price in whole pence"
  return scaled / divisor

def answer (input : Json) : Except String Json := do
  let date ← dateNumber (← input.getObjValAs? String "effective_date")
  let price ← pricePence (← input.getObjVal? "price_pounds")
  let some tax := Sdlt.taxAt date price | throw "date outside the SDLT model"
  return Json.mkObj [("tax_pounds", toJson tax)]

def main : IO Unit := do
  let stdin ← IO.getStdin
  let input ← IO.ofExcept (Json.parse (← stdin.readToEnd))
  IO.println (← IO.ofExcept (answer input)).compress
