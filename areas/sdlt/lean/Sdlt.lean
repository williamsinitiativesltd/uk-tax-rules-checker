/-!
# Stamp Duty Land Tax: how the legislation stacks, proved in Lean 4

A small model of how the residential rates in Finance Act 2003 section 55 have been built up in layers since
December 2014, with theorems the Lean proof checker verifies about it.

* **Amendments** change the Act's text from a date: the slab system (the whole price at one rate) gave way to the slice
  system (each rate on its part of the price) for effective dates from 4 December 2014 (SDLT Act 2015 s1 and s2(2)).
* **Modifications** leave the text alone and override it for a period: the temporary reliefs of the 2020 Act (s1, its
  end date substituted by Finance Act 2021 s87(2); and s1A, inserted by Finance Act 2021 s87(3)) and of the 2023 Act.

The rule in force on a date is the modification in force, if any, otherwise the Act's text in force. The theorems
show that the layers never conflict, that the reliefs end, what each relief is worth at most, that the slice system
has no cliff edges where the slab system had a £5,000 one, and that the worked examples come out right.

Money is in pence (`Nat`) and rates in whole percent, so every calculation is exact; `pounds` rounds down to the
pound (HMRC's manual SDLTM00050). Dates are `yyyymmdd` numbers, which keep their order.

Sources (legislation.gov.uk and GOV.UK, read 25 and 26 Nov 2026): FA 2003 s55 (current and as at 3 Dec 2014); SDLT
Act 2015 s2; SDLT (Temporary Relief) Act 2020 s1 and s1A; SDLT (Temporary Relief) Act 2023 s1.

Scope: standard residential rates only, for effective dates from 3 December 2014. Not modelled: the higher rates,
the 17% rate, the non-resident surcharge, reliefs, linked transactions, leases, Table B. Built by an AI agent; not
reviewed by a tax professional. Not advice.
-/

namespace Sdlt

/-! ## Money, bands and the two ways of charging -/


/-- Whole pounds, in pence. -/
def gbp (n : Nat) : Nat := n * 100

/-- A row of a slice table: the part of the consideration above `lower` and up to `upper`, at `rate` percent. -/
structure Band where
  lower : Nat
  upper : Option Nat
  rate  : Nat
deriving Repr, DecidableEq

abbrev Table := List Band

/-- s55(1B) Step 1: the part of the consideration that falls in a band. -/
def part (b : Band) (p : Nat) : Nat :=
  match b.upper with
  | none   => p - b.lower
  | some u => min p u - b.lower

/-- s55(1B) Steps 1 and 2, exactly: the sum of rate times part, in pence times percent. -/
def sliceScaled : Table → Nat → Nat
  | [],     _ => 0
  | b :: t, p => b.rate * part b p + sliceScaled t p

/-- A row of a slab table: consideration up to `upper` is charged, all of it, at `rate` percent. -/
structure SlabBand where
  upper : Option Nat
  rate  : Nat
deriving Repr, DecidableEq

/-- The old s55(1) and (2): one percentage, found from the band the whole consideration falls in. -/
def slabRate : List SlabBand → Nat → Nat
  | [],     _ => 0
  | s :: t, p =>
    match s.upper with
    | none   => s.rate
    | some u => if p ≤ u then s.rate else slabRate t p

/-- The old s55(1): that percentage of the whole consideration, in pence times percent. -/
def slabScaled (t : List SlabBand) (p : Nat) : Nat := slabRate t p * p

/-- Nat times percent to whole pounds, rounded down (SDLTM00050). -/
def pounds (scaled : Nat) : Nat := scaled / 10000

/-! ## The tables, each in the Act's own bands -/

/-- FA 2003 s55(2) Table A as it stood on 3 December 2014: the slab system. -/
def slab2014 : List SlabBand :=
  [⟨some (gbp 125000), 0⟩, ⟨some (gbp 250000), 1⟩, ⟨some (gbp 500000), 3⟩,
   ⟨some (gbp 1000000), 4⟩, ⟨some (gbp 2000000), 5⟩, ⟨none, 7⟩]

/-- FA 2003 s55(1B) Table A, the slice system, unmodified (from 4 December 2014, and today). -/
def sliceBase : Table :=
  [⟨0, some (gbp 125000), 0⟩, ⟨gbp 125000, some (gbp 250000), 2⟩, ⟨gbp 250000, some (gbp 925000), 5⟩,
   ⟨gbp 925000, some (gbp 1500000), 10⟩, ⟨gbp 1500000, none, 12⟩]

/-- The shape every temporary relief used: a wider nil-rate band, the upper bands unchanged. -/
def nilBand (top : Nat) : Table :=
  [⟨0, some (gbp top), 0⟩, ⟨gbp top, some (gbp 925000), 5⟩,
   ⟨gbp 925000, some (gbp 1500000), 10⟩, ⟨gbp 1500000, none, 12⟩]

/-- SDLT (Temporary Relief) Act 2020 s1(2): nil rate to £500,000. -/
def relief500 : Table := nilBand 500000

/-- SDLT (Temporary Relief) Act 2020 s1A(2) and SDLT (Temporary Relief) Act 2023 s1(2): nil rate to £250,000. -/
def relief250 : Table := nilBand 250000

/-! ## The layers -/

inductive Rule where
  | slab  (t : List SlabBand)
  | slice (t : Table)

def Rule.scaled : Rule → Nat → Nat
  | .slab t,  p => slabScaled t p
  | .slice t, p => sliceScaled t p


/-- The effective dates a layer covers, both ends included; `none` means still in force. -/
structure Window where
  start : Nat
  stop  : Option Nat

def Window.contains (w : Window) (d : Nat) : Bool :=
  decide (w.start ≤ d) &&
    (match w.stop with
     | none   => true
     | some s => decide (d ≤ s))

inductive Kind where
  | amendment     -- changes the Act's text from a date
  | modification  -- leaves the text alone and overrides it for a period

structure Layer where
  name   : String
  source : String
  kind   : Kind
  window : Window
  rule   : Rule

def slabLayer : Layer where
  name   := "slab system"
  source := "FA 2003 s55(1) and (2), Table A, as at 3 Dec 2014 (the model starts on that date)"
  kind   := .amendment
  window := ⟨20141203, some 20141203⟩
  rule   := .slab slab2014

def sliceLayer : Layer where
  name   := "slice system"
  source := "FA 2003 s55(1B), Table A, inserted by SDLT Act 2015 s1, for effective dates from 4 Dec 2014 (s2(2))"
  kind   := .amendment
  window := ⟨20141204, none⟩
  rule   := .slice sliceBase

def relief2020 : Layer where
  name   := "2020 relief"
  source := "SDLT (Temporary Relief) Act 2020 s1; end date substituted by FA 2021 s87(2)"
  kind   := .modification
  window := ⟨20200708, some 20210630⟩
  rule   := .slice relief500

def relief2021 : Layer where
  name   := "2021 relief"
  source := "SDLT (Temporary Relief) Act 2020 s1A, inserted by FA 2021 s87(3)"
  kind   := .modification
  window := ⟨20210701, some 20210930⟩
  rule   := .slice relief250

def relief2023 : Layer where
  name   := "2022 to 2025 relief"
  source := "SDLT (Temporary Relief) Act 2023 s1(1) and (2)"
  kind   := .modification
  window := ⟨20220923, some 20250331⟩
  rule   := .slice relief250

def amendments    : List Layer := [slabLayer, sliceLayer]
def modifications : List Layer := [relief2020, relief2021, relief2023]

def firstIn : List Layer → Nat → Option Layer
  | [],      _ => none
  | l :: ls, d => if l.window.contains d then some l else firstIn ls d

/-- The layer in force: a modification in force overrides the Act's text; otherwise the text in force applies. -/
def layerAt (d : Nat) : Option Layer :=
  match firstIn modifications d with
  | some l => some l
  | none   => firstIn amendments d

/-- The tax in whole pounds on a price in pence with an effective date, if the model covers the date. -/
def taxAt (d : Nat) (p : Nat) : Option Nat :=
  (layerAt d).map fun l => pounds (l.rule.scaled p)

/-! ## The layers fit together -/

def Window.before (a b : Window) : Bool :=
  match a.stop with
  | none   => false
  | some s => decide (s < b.start)

def Window.disjoint (a b : Window) : Bool := a.before b || b.before a

def pairwiseDisjoint : List Layer → Bool
  | []      => true
  | l :: ls => ls.all (fun m => l.window.disjoint m.window) && pairwiseDisjoint ls

/-- No two temporary reliefs are ever in force on the same day. -/
theorem modifications_never_overlap : pairwiseDisjoint modifications = true := by decide

/-- The Act never has two texts in force on the same day. -/
theorem amendments_never_overlap : pairwiseDisjoint amendments = true := by decide

/-- Every relief modifies the slice system: none reaches back into the slab era. -/
theorem reliefs_all_in_slice_era :
    modifications.all (fun m => decide (sliceLayer.window.start ≤ m.window.start)) = true := by decide

/-- Every date the model covers has exactly one rule: the text in force is never missing. -/
theorem always_a_rule (d : Nat) (h : 20141203 ≤ d) : (layerAt d).isSome = true := by
  unfold layerAt
  split
  · rfl
  · simp only [firstIn, amendments, slabLayer, sliceLayer, Window.contains]
    by_cases h1 : d ≤ 20141203
    · simp [h, h1]
    · have h2 : 20141204 ≤ d := by omega
      simp [h1, h2]

/-- The reliefs are over: from 1 April 2025 the unmodified slice table applies. -/
theorem reliefs_end (d : Nat) (h : 20250331 < d) :
    (layerAt d).map (·.name) = some "slice system" := by
  have hm : firstIn modifications d = none := by
    simp only [firstIn, modifications, relief2020, relief2021, relief2023, Window.contains]
    have a : ¬ d ≤ 20210630 := by omega
    have b : ¬ d ≤ 20210930 := by omega
    have c : ¬ d ≤ 20250331 := by omega
    simp [a, b, c]
  have hs : ¬ d ≤ 20141203 := by omega
  have ht : 20141204 ≤ d := by omega
  simp [layerAt, hm, firstIn, amendments, slabLayer, sliceLayer, Window.contains, hs, ht]

/-! ## The worked examples (the same as the Python demo's tests) -/

/-- GOV.UK's worked example: £295,000 in April 2025, £4,750. -/
theorem worked_example : taxAt 20250415 (gbp 295000) = some 4750 := by decide

/-- The same price on the last day of the 2022 to 2025 relief: £2,250. -/
theorem day_before_change : taxAt 20250331 (gbp 295000) = some 2250 := by decide

/-- During the 2020 relief: nothing. -/
theorem during_2020_relief : taxAt 20210101 (gbp 295000) = some 0 := by decide

/-- On the last day of the slab system: 3% of the whole price, £8,850. -/
theorem last_slab_day : taxAt 20141203 (gbp 295000) = some 8850 := by decide

/-- The next day, under the slice system: £4,750. -/
theorem first_slice_day : taxAt 20141204 (gbp 295000) = some 4750 := by decide

/-! ## Why the slice system replaced the slab system -/

/-- Under the slab system, one penny over £250,000 added £5,000 of tax: a cliff edge. -/
theorem slab_cliff :
    pounds (slabScaled slab2014 (gbp 250000 + 1)) = pounds (slabScaled slab2014 (gbp 250000)) + 5000 := by
  decide

/-- Under the slice system the same penny adds nothing you can see. -/
theorem slice_same_penny :
    pounds (sliceScaled sliceBase (gbp 250000 + 1)) = pounds (sliceScaled sliceBase (gbp 250000)) := by
  decide

/-- One band's part never shrinks as the price rises. -/
theorem part_mono (b : Band) {p q : Nat} (h : p ≤ q) : part b p ≤ part b q := by
  unfold part
  split
  · omega
  · simp only [Nat.min_def]
    split <;> split <;> omega

/-- Under any slice table, whatever its rates, a higher price never means less tax. -/
theorem slice_mono (t : Table) {p q : Nat} (h : p ≤ q) : sliceScaled t p ≤ sliceScaled t q := by
  induction t with
  | nil => simp [sliceScaled]
  | cons b t ih =>
    simp only [sliceScaled]
    have := Nat.mul_le_mul_left b.rate (part_mono b h)
    omega

/-- No cliff edges, at any price: one more penny never adds more than 12% of a penny. -/
theorem slice_no_cliff (p : Nat) : sliceScaled sliceBase (p + 1) ≤ sliceScaled sliceBase p + 12 := by
  have key : ∀ q, q = p + 1 → sliceScaled sliceBase q ≤ sliceScaled sliceBase p + 12 := by
    intro q hq
    simp only [sliceScaled, sliceBase, part, gbp, Nat.min_def]
    repeat' split
    all_goals omega
  exact key _ rfl

/-- And the tax is never more than 12% of the price. -/
theorem slice_at_most_12_percent (p : Nat) : sliceScaled sliceBase p ≤ 12 * p := by
  simp only [sliceScaled, sliceBase, part, gbp, Nat.min_def]
  repeat' split
  all_goals omega

/-! ## What each relief is worth -/

/-- A relief never raises the tax, at any price. -/
theorem relief250_never_raises (p : Nat) : sliceScaled relief250 p ≤ sliceScaled sliceBase p := by
  simp only [sliceScaled, relief250, nilBand, sliceBase, part, gbp, Nat.min_def]
  repeat' split
  all_goals omega

/-- The £250,000 nil-rate band saves at most £2,500, at any price. -/
theorem relief250_at_most_2500 (p : Nat) :
    sliceScaled sliceBase p ≤ sliceScaled relief250 p + 2500 * 10000 := by
  simp only [sliceScaled, relief250, nilBand, sliceBase, part, gbp, Nat.min_def]
  repeat' split
  all_goals omega

/-- ...and exactly £2,500 on any price of £250,000 or more. -/
theorem relief250_exactly_2500 (p : Nat) (h : gbp 250000 ≤ p) :
    sliceScaled sliceBase p = sliceScaled relief250 p + 2500 * 10000 := by
  simp only [gbp] at h
  simp only [sliceScaled, relief250, nilBand, sliceBase, part, gbp, Nat.min_def]
  repeat' split
  all_goals omega

/-- The 2020 relief's £500,000 nil-rate band saved at most £15,000. -/
theorem relief500_at_most_15000 (p : Nat) :
    sliceScaled sliceBase p ≤ sliceScaled relief500 p + 15000 * 10000 := by
  simp only [sliceScaled, relief500, nilBand, sliceBase, part, gbp, Nat.min_def]
  repeat' split
  all_goals omega

/-! ## The 2015 Act's transitional election (s2(3)) -/

/-- A purchaser who could elect (s2(3) to (5)) paid the lower of the two. -/
def withElection (p : Nat) : Nat := min (slabScaled slab2014 p) (sliceScaled sliceBase p)

/-- Electing never costs more than either system alone. -/
theorem election_never_costs_more (p : Nat) :
    withElection p ≤ sliceScaled sliceBase p ∧ withElection p ≤ slabScaled slab2014 p :=
  ⟨Nat.min_le_right _ _, Nat.min_le_left _ _⟩

/-- The election mattered: at £1,000,000 the old slab system was cheaper (£40,000 against £43,750)... -/
theorem old_rules_cheaper_at_1m :
    slabScaled slab2014 (gbp 1000000) < sliceScaled sliceBase (gbp 1000000) := by decide

/-- ...while at £200,000 the new slice system was (£1,500 against £2,000). -/
theorem new_rules_cheaper_at_200k :
    sliceScaled sliceBase (gbp 200000) < slabScaled slab2014 (gbp 200000) := by decide

end Sdlt
