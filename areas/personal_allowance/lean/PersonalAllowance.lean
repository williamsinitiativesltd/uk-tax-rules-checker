/-!
# The income tax personal allowance and its taper, proved in Lean 4

A model of Income Tax Act 2007 section 35 (the personal allowance), read with section 58 (adjusted net income), and
the theorems the Lean proof checker verifies about it. The second area of law in WIL's Rules as Code prototype, after
Finance Act 2003 s55 (`../lean/Sdlt.lean`).

* **The amount over time.** Two kinds of provision set the s35(1) amount for a tax year, as for SDLT:
  * **text substitutions** change the sum written in s35(1), and it stands until the next one (Finance Acts and the
    Treasury's indexation orders under s57);
  * **modifications** specify the amount for named tax years and leave the text alone (FA 2015 s5; FA 2021 s5,
    extended by FA 2023 s5 and FA 2026 s10).
  The provision that governs a tax year is the latest made of those covering it. A provision amended in place (such
  as FA 2021 s5) counts as made on the date of its latest amendment. The theorems check that this reading and the
  other natural one (a modification beats the text) give the same amount for every year modelled.
* **The taper** (s35(2) to (3), inserted by FA 2009 s4(1) for 2010-11 on, s4(4)): the allowance is reduced by half of
  adjusted net income above £100,000, and what remains, if not a whole pound, is rounded up to the next pound.
* **The rates** for one tax year, 2026-27, to show the "60% band": FA 2026 s2 (20%, 40%, 45%); the basic rate limit
  £37,700 (ITA s10(5), as specified by FA 2021 s5(1) as extended); the higher rate limit in ITA s10(5A), substituted by
  FA 2023 s6, which is twice the personal allowance plus £100,000, £125,140.

Money is in pence (`Nat`), allowances in whole pounds, rates in whole percent; tax on each band is rounded down to the
penny. Tax years are named by the year they start in: 2026 means 2026-27. Income goes on a return in whole pounds,
rounded down (HMRC's Business Income Manual BIM31047 and the return's notes), so the theorems that matter to a
taxpayer are those in whole pounds; the penny ones show only how the rounding in s35(3) works.

Sources (legislation.gov.uk and GOV.UK, read 26 Nov 2026): ITA 2007 s35 (current, and as at 6 Apr 2010, 20 Jul 2011,
6 Apr 2012, 18 Jul 2012, 18 Jul 2013, 6 Apr 2014, 18 Jul 2014, 6 Apr 2016, 16 Sep 2016, 30 Nov 2017, 6 Apr 2018,
6 Apr 2020), s57 and s58; FA 2009 s4; FA 2014 s2; FA 2015 s5; F(No.2)A 2015 s5; FA 2016 s3; FA 2021 s5; FA 2023 s5
and s6; FA 2026 s2 and s10; GOV.UK "Income Tax rates and allowances for current and previous tax years" (updated 6
Apr 2026), "Income over £100,000" and "Adjusted net income" (updated 30 May 2025).

Scope: the basic personal allowance only; one tax year's rates (2026-27, England, Wales and Northern Ireland,
non-savings income); adjusted net income taken as given. Not modelled: the age-related allowances, blind person's
allowance, the marriage allowance, Scottish and Welsh rates, savings and dividend rates, s57 indexation after
2030-31. Built by an AI agent; not reviewed by a tax professional. Not advice.
-/

namespace PersonalAllowance

/-! ## The amount over time -/

/-- How a provision sets the amount: by changing s35(1)'s text, or by specifying it for named years. -/
inductive Kind
  | text
  | modification
deriving Repr, DecidableEq

/-- A provision that sets the s35(1) amount. `made` is a `yyyymmdd` date: when the provision, in the form that
governs, was made. `first` and `last` are tax years; a text substitution has no `last` (it stands until replaced). -/
structure Provision where
  source : String
  kind   : Kind
  made   : Nat
  first  : Nat
  last   : Option Nat
  amount : Nat
deriving Repr, DecidableEq

def Provision.covers (p : Provision) (y : Nat) : Bool :=
  decide (p.first ≤ y) && (match p.last with
    | none   => true
    | some l => decide (y ≤ l))

def fa2009 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by FA 2009 s3(1)(a) (21 Jul 2009)"
    kind := .text, made := 20090721, first := 2009, last := none, amount := 6475 }
def fa2011 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by FA 2011 s3(1) (19 Jul 2011)"
    kind := .text, made := 20110719, first := 2011, last := none, amount := 7475 }
def order2011 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by the Income Tax (Indexation) Order 2011, SI 2011/2926, art 3(a)"
    kind := .text, made := 20111206, first := 2012, last := none, amount := 7895 }
def fa2012 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by FA 2012 s3(1) (17 Jul 2012)"
    kind := .text, made := 20120717, first := 2012, last := none, amount := 8105 }
def fa2013 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by FA 2013 s2(1) (17 Jul 2013)"
    kind := .text, made := 20130717, first := 2013, last := none, amount := 9440 }
def order2013 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by the Income Tax (Indexation) Order 2013, SI 2013/3088, art 3(a)"
    kind := .text, made := 20131205, first := 2014, last := none, amount := 9740 }
def fa2014s1 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted by FA 2014 s1(3)(b) (17 Jul 2014)"
    kind := .text, made := 20140717, first := 2014, last := none, amount := 10000 }
def fa2014s2 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted for 2015-16 by FA 2014 s2(1)(b), its sum substituted by FA 2015 s3(2) (26 Mar 2015)"
    kind := .text, made := 20150326, first := 2015, last := none, amount := 10600 }
def fa2015a : Provision :=
  { source := "FA 2015 s5(1)(a), for 2016-17, its sum substituted by F(No.2)A 2015 s5(a) (18 Nov 2015)"
    kind := .modification, made := 20151118, first := 2016, last := some 2016, amount := 11000 }
def fa2015b : Provision :=
  { source := "FA 2015 s5(1)(b), for 2017-18, its sum substituted by FA 2016 s3(1) (15 Sep 2016)"
    kind := .modification, made := 20160915, first := 2017, last := some 2017, amount := 11500 }
def order2017 : Provision :=
  { source := "ITA 2007 s35(1), sum substituted for 2018-19 by the Income Tax (Indexation) Order 2017, SI 2017/1184, arts 1 and 3(a)"
    kind := .text, made := 20171130, first := 2018, last := none, amount := 11850 }
def fa2019 : Provision :=
  { source := "ITA 2007 s35(1), sum specified for 2019-20 and 2020-21 by FA 2019 s5(2) (12 Feb 2019)"
    kind := .text, made := 20190212, first := 2019, last := none, amount := 12500 }
def order2021 : Provision :=
  { source := "ITA 2007 s35(1), sum specified for 2021-22 by the Income Tax (Indexation) Order 2021, SI 2021/111, art 3(a)"
    kind := .text, made := 20210201, first := 2021, last := none, amount := 12570 }
def fa2021 : Provision :=
  { source := "FA 2021 s5(2), years extended by FA 2023 s5(3) (10 Jan 2023) and FA 2026 s10(3) (18 Mar 2026)"
    kind := .modification, made := 20260318, first := 2022, last := some 2030, amount := 12570 }

def provisions : List Provision :=
  [fa2009, fa2011, order2011, fa2012, fa2013, order2013, fa2014s1, fa2014s2, fa2015a, fa2015b, order2017, fa2019,
   order2021, fa2021]

/-- The governing provision for tax year `y`: the latest made of those covering it. -/
def pick (y : Nat) : List Provision → Option Provision
  | [] => none
  | p :: ps =>
    if p.covers y then
      match pick y ps with
      | none   => some p
      | some q => if q.made ≤ p.made then some p else some q
    else pick y ps

/-- The other natural reading: the latest modification covering the year if there is one, otherwise the latest text. -/
def pickModFirst (y : Nat) (ps : List Provision) : Option Provision :=
  match pick y (ps.filter (·.kind == .modification)) with
  | some m => some m
  | none   => pick y (ps.filter (·.kind == .text))

/-- The s35(1) amount for tax year `y`, in pounds. -/
def amountFor (y : Nat) : Option Nat := (pick y provisions).map (·.amount)

/-! ## The taper: s35(2) and (3) -/

/-- s35(2): the income limit, in pounds (never changed since 2010-11). -/
def incomeLimit : Nat := 100000

/-- Adjusted net income (s58) above the income limit, in pence. -/
def excess (ani : Nat) : Nat := ani - 100 * incomeLimit

/-- s35(2) and (3): the allowance in whole pounds for full amount `a` (pounds) and adjusted net income `ani`
(pence). In half-pence the full amount is `200 * a` and the reduction, half the excess in pence, is `excess ani`;
what remains is rounded up to a whole pound (s35(3)), and never falls below nil. -/
def allowance (a ani : Nat) : Nat := (200 * a - excess ani + 199) / 200

/-- The allowance for tax year `y`: the full amount before 2010-11 (no taper), the tapered amount from then on. -/
def allowanceFor (y ani : Nat) : Option Nat :=
  (amountFor y).map fun a => if y < 2010 then a else allowance a ani

/-! ## The rates for 2026-27 -/

def paToday : Nat := 12570
/-- ITA s10(5), £37,700 for 2026-27 (FA 2021 s5(1), as extended by FA 2023 s5(2)). -/
def basicLimit : Nat := 37700
/-- ITA s10(5A), substituted by FA 2023 s6: twice the s35(1) amount plus the income limit. -/
def higherLimit : Nat := 2 * paToday + incomeLimit

/-- Taxable income in pence, all of it non-savings income with no other deductions, so that adjusted net income is
the whole income. -/
def taxable (ani : Nat) : Nat := ani - 100 * allowance paToday ani

/-- FA 2026 s2: 20% to the basic rate limit, 40% to the higher rate limit, 45% above; each band rounded down to the
penny. -/
def bandTax (t : Nat) : Nat :=
  (20 * min t (100 * basicLimit)) / 100
    + (40 * (min t (100 * higherLimit) - 100 * basicLimit)) / 100
    + (45 * (t - 100 * higherLimit)) / 100

/-- Income tax for 2026-27 in pence on adjusted net income `ani` in pence. -/
def tax2026 (ani : Nat) : Nat := bandTax (taxable ani)

/-! ## Theorems: the amount over time -/

/-- No two provisions were made on the same day, so "the latest made" is never a tie. -/
theorem made_dates_distinct : (provisions.map (·.made)).Nodup := by decide

/-- The amount for every tax year from 2010-11 to 2030-31, as the provisions resolve it. -/
theorem amounts_by_year :
    (List.range 21).map (fun i => amountFor (2010 + i)) =
      [some 6475, some 7475, some 8105, some 9440, some 10000, some 10600, some 11000, some 11500, some 11850,
       some 12500, some 12500, some 12570, some 12570, some 12570, some 12570, some 12570, some 12570, some 12570,
       some 12570, some 12570, some 12570] := by decide

/-- Both readings of how the provisions stack give the same amount for every tax year from 2009-10 to 2031-32. -/
theorem two_readings_agree :
    ∀ i, i < 23 → (pick (2009 + i) provisions).map (·.amount) =
      (pickModFirst (2009 + i) provisions).map (·.amount) := by decide

/-- A step for the next theorem: if any provision covers a year, some provision governs it. -/
theorem pick_some_of_mem (y : Nat) :
    ∀ (ps : List Provision) (p : Provision), p ∈ ps → p.covers y = true → (pick y ps).isSome = true
  | [], _, h, _ => by simp at h
  | q :: qs, p, h, hc => by
    rcases List.mem_cons.mp h with rfl | ht
    · simp only [pick, hc, ↓reduceIte]
      cases pick y qs with
      | none => rfl
      | some r => by_cases hm : r.made ≤ p.made <;> simp [hm]
    · have ih := pick_some_of_mem y qs p ht hc
      by_cases hq : q.covers y = true
      · simp only [pick, hq, ↓reduceIte]
        cases hr : pick y qs with
        | none => rfl
        | some r => by_cases hm : r.made ≤ q.made <;> simp [hm]
      · simp only [pick, hq]
        exact ih

/-- Every tax year from 2009-10 on has an amount: no gaps. -/
theorem always_an_amount (y : Nat) (h : 2009 ≤ y) : (amountFor y).isSome = true := by
  have hc : fa2009.covers y = true := by
    simp [Provision.covers, fa2009, h]
  have hm : fa2009 ∈ provisions := by simp [provisions]
  have := pick_some_of_mem y provisions fa2009 hm hc
  simpa [amountFor] using this

/-- A later Finance Act overtook the indexation order for the same year: the order's £7,895 covers 2012-13, but
FA 2012's £8,105 governs. -/
theorem fa2012_overtakes_order : order2011.covers 2012 = true ∧ amountFor 2012 = some 8105 := by decide

/-- The same in 2014-15: the order's £9,740, overtaken by FA 2014's £10,000. -/
theorem fa2014_overtakes_order : order2013.covers 2014 = true ∧ amountFor 2014 = some 10000 := by decide

/-- A modification beats the text: in 2016-17 s35(1)'s text still read £10,600, but FA 2015 s5 gave £11,000. -/
theorem modification_over_text_2016 :
    fa2014s2.covers 2016 = true ∧ (pick 2016 provisions).map (·.source) = some fa2015a.source ∧
      amountFor 2016 = some 11000 := by decide

/-- When the freeze ends, the model falls back to s35(1)'s text: for 2031-32 the governing provision is SI 2021/111.
In law s57 indexation would then apply, which the model leaves out, so it stops at 2030-31. -/
theorem after_freeze_text_returns : (pick 2031 provisions).map (·.source) = some order2021.source := by decide

/-- No taper before 2010-11: in 2009-10 an income of £1m kept the full £6,475. -/
theorem no_taper_in_2009 : allowanceFor 2009 (100 * 1000000) = some 6475 := by decide

/-- The income at which the allowance reaches nil, for every tax year from 2010-11 to 2030-31: the limit plus twice
the amount. -/
theorem nil_points_by_year :
    (List.range 21).map (fun i => (amountFor (2010 + i)).map (fun a => incomeLimit + 2 * a)) =
      [some 112950, some 114950, some 116210, some 118880, some 120000, some 121200, some 122000, some 123000,
       some 123700, some 125000, some 125000, some 125140, some 125140, some 125140, some 125140, some 125140,
       some 125140, some 125140, some 125140, some 125140, some 125140] := by decide

/-! ## Theorems: the taper, for every amount and every income -/

/-- The allowance never exceeds the full amount (and, as a whole number of pounds, is never negative). -/
theorem allowance_le_full (a ani : Nat) : allowance a ani ≤ a := by
  unfold allowance excess incomeLimit
  omega

/-- Up to £100,000 of adjusted net income, the full amount. -/
theorem full_up_to_limit (a ani : Nat) (h : ani ≤ 100 * incomeLimit) : allowance a ani = a := by
  have he : excess ani = 0 := by
    unfold excess
    omega
  unfold allowance
  rw [he]
  omega

/-- The allowance never rises as income rises. -/
theorem allowance_antitone (a : Nat) {ani ani' : Nat} (h : ani ≤ ani') : allowance a ani' ≤ allowance a ani := by
  unfold allowance excess incomeLimit
  omega

/-- Nil from the limit plus twice the amount. -/
theorem nil_from (a ani : Nat) (h : 100 * (incomeLimit + 2 * a) ≤ ani) : allowance a ani = 0 := by
  unfold allowance excess incomeLimit at *
  omega

/-- And not before: below that income some allowance remains (for any amount above nil; Lean refused the statement
without that condition, rightly). -/
theorem positive_below (a ani : Nat) (ha : 0 < a) (h : ani < 100 * (incomeLimit + 2 * a)) :
    0 < allowance a ani := by
  unfold allowance excess incomeLimit at *
  omega

/-- £1 of allowance is lost for every £2 of income in the taper band. -/
theorem pound_per_two (a ani n : Nat) (h1 : 100 * incomeLimit ≤ ani)
    (h2 : ani + 200 * n ≤ 100 * (incomeLimit + 2 * a)) :
    allowance a (ani + 200 * n) + n = allowance a ani := by
  unfold allowance excess incomeLimit at *
  omega

/-- s35(3): the allowance is the exact reduced amount rounded up to the next whole pound, so never less than exact and
less than £1 more. -/
theorem rounds_up (a ani : Nat) :
    200 * a - excess ani ≤ 200 * allowance a ani ∧ 200 * allowance a ani < 200 * a - excess ani + 200 := by
  unfold allowance
  omega

/-- At today's £12,570: nil from £125,140 ... -/
theorem nil_from_125140 (ani : Nat) (h : 100 * 125140 ≤ ani) : allowance paToday ani = 0 :=
  nil_from paToday ani (by unfold paToday incomeLimit; omega)

/-- ... and above nil below it. -/
theorem positive_below_125140 (ani : Nat) (h : ani < 100 * 125140) : 0 < allowance paToday ani :=
  positive_below paToday ani (by unfold paToday; omega) (by unfold paToday incomeLimit; omega)

/-- The additional rate starts exactly where the allowance runs out: s10(5A) as substituted by FA 2023 s6. -/
theorem higher_limit_is_where_allowance_ends (ani : Nat) :
    allowance paToday ani = 0 ↔ 100 * higherLimit ≤ ani := by
  unfold allowance excess higherLimit paToday incomeLimit
  omega

/-! ## Theorems: the 60% band in 2026-27 -/

/-- A step: in 2026-27 the allowance is at most £12,570. -/
theorem allowance_today_le (ani : Nat) : allowance paToday ani ≤ 12570 := allowance_le_full paToday ani

/-- Inside the taper band taxable income lies between the basic rate limit and the higher rate limit, so any extra
taxable income falls in the higher rate band (the first £37,700 stays at 20%). -/
theorem taper_band_is_higher_rate (ani : Nat) (h1 : 100 * incomeLimit ≤ ani) (h2 : ani ≤ 100 * higherLimit) :
    100 * basicLimit ≤ taxable ani ∧ taxable ani ≤ 100 * higherLimit := by
  have := allowance_today_le ani
  unfold taxable basicLimit higherLimit paToday incomeLimit at *
  omega

/-- On the higher rate band, tax is the basic band's £7,540 plus 40% of the rest. -/
theorem bandTax_higher (t : Nat) (h1 : 100 * basicLimit ≤ t) (h2 : t ≤ 100 * higherLimit) :
    bandTax t = 754000 + (40 * (t - 100 * basicLimit)) / 100 := by
  unfold bandTax basicLimit higherLimit paToday incomeLimit at *
  simp only [Nat.min_def]
  repeat' split
  all_goals omega

/-- The 60% band: inside the taper band each extra £2 of income costs £1.20 of tax, 60p for each £1. -/
theorem sixty_percent_band (ani n : Nat) (h1 : 100 * incomeLimit ≤ ani) (h2 : ani + 200 * n ≤ 100 * higherLimit) :
    tax2026 (ani + 200 * n) = tax2026 ani + 120 * n := by
  have hstep := pound_per_two paToday ani n h1 (by unfold higherLimit at h2; exact h2)
  have b1 := taper_band_is_higher_rate ani h1 (by omega)
  have b2 := taper_band_is_higher_rate (ani + 200 * n) (by omega) h2
  have ht : taxable (ani + 200 * n) = taxable ani + 300 * n := by
    have := allowance_today_le ani
    unfold taxable paToday incomeLimit at *
    omega
  unfold tax2026
  rw [bandTax_higher _ b2.1 b2.2, bandTax_higher _ b1.1 b1.2, ht]
  unfold basicLimit higherLimit paToday incomeLimit at *
  omega

/-- And never more than that over any stretch of the band: 60% of the extra income, give or take 41p from s35(3)'s
rounding of the allowance to whole pounds. -/
theorem sixty_percent_at_most (ani d : Nat) (h1 : 100 * incomeLimit ≤ ani) (h2 : ani + d ≤ 100 * higherLimit) :
    100 * tax2026 (ani + d) ≤ 100 * tax2026 ani + 60 * d + 4100 ∧
      100 * tax2026 ani + 60 * d ≤ 100 * tax2026 (ani + d) + 4100 := by
  have b1 := taper_band_is_higher_rate ani h1 (by omega)
  have b2 := taper_band_is_higher_rate (ani + d) (by omega) h2
  have r1 := rounds_up paToday ani
  have r2 := rounds_up paToday (ani + d)
  have l1 := allowance_today_le ani
  have l2 := allowance_today_le (ani + d)
  unfold tax2026
  rw [bandTax_higher _ b2.1 b2.2, bandTax_higher _ b1.1 b1.2]
  unfold taxable excess basicLimit higherLimit paToday incomeLimit at *
  omega

/-- Maths only: the rounding in s35(3) shows at the penny, as one more penny of income, from £100,001.99 to £100,002,
takes £1 off the allowance and adds 41p of tax. A return carries whole pounds, so no taxpayer meets this; the
whole-pound theorems below are the ones that apply. -/
theorem one_penny_step :
    allowance paToday 10000200 + 1 = allowance paToday 10000199 ∧ tax2026 10000200 = tax2026 10000199 + 41 := by
  decide

/-- Below the band, at the higher rate, each extra £1 costs 40p. -/
theorem forty_percent_below (ani n : Nat) (h1 : 100 * (basicLimit + paToday) ≤ ani)
    (h2 : ani + 100 * n ≤ 100 * incomeLimit) : tax2026 (ani + 100 * n) = tax2026 ani + 40 * n := by
  have f1 := full_up_to_limit paToday ani (by omega)
  have f2 := full_up_to_limit paToday (ani + 100 * n) h2
  unfold tax2026 taxable
  rw [f1, f2]
  unfold basicLimit paToday incomeLimit at *
  rw [bandTax_higher _ (by unfold basicLimit; omega) (by unfold higherLimit paToday incomeLimit; omega),
    bandTax_higher _ (by unfold basicLimit; omega) (by unfold higherLimit paToday incomeLimit; omega)]
  unfold basicLimit
  omega

/-- Above the band, at the additional rate, each extra £1 costs 45p. -/
theorem forty_five_percent_above (ani n : Nat) (h : 100 * higherLimit ≤ ani) :
    tax2026 (ani + 100 * n) = tax2026 ani + 45 * n := by
  have z1 := (higher_limit_is_where_allowance_ends ani).mpr h
  have z2 := (higher_limit_is_where_allowance_ends (ani + 100 * n)).mpr (by omega)
  unfold tax2026 taxable
  rw [z1, z2]
  unfold bandTax basicLimit higherLimit paToday incomeLimit at *
  simp only [Nat.min_def]
  repeat' split
  all_goals omega

/-- The whole band costs 60% of its £25,140: £15,084 more tax at £125,140 than at £100,000. -/
theorem whole_band : tax2026 (100 * 125140) = tax2026 (100 * 100000) + 1508400 := by decide

/-! ## Theorems: whole pounds, as income goes on a return -/

/-- At an even number of pounds into the band, `2k` above £100,000, the allowance is exactly `k` pounds below the full
amount: no rounding comes in. -/
theorem whole_pound_even (a k : Nat) (h : k ≤ a) : allowance a (100 * (incomeLimit + 2 * k)) = a - k := by
  unfold allowance excess incomeLimit
  omega

/-- The step in whole pounds: an odd pound into the band leaves the allowance where the even pound below left it (half
of that pound is 50p, and s35(3) rounds the allowance up to the whole pound), and the next even pound takes £1 off. -/
theorem whole_pound_step (a k : Nat) (h : 2 * k + 2 ≤ 2 * a) :
    allowance a (100 * (incomeLimit + 2 * k + 1)) = allowance a (100 * (incomeLimit + 2 * k)) ∧
      allowance a (100 * (incomeLimit + 2 * k + 2)) + 1 = allowance a (100 * (incomeLimit + 2 * k + 1)) := by
  unfold allowance excess incomeLimit
  omega

/-- The whole-pound nil point, for any full amount: £1 of allowance remains at £1 below the limit plus twice the
amount (half of the odd pound, rounded up), and nil at it. -/
theorem whole_pound_nil (a : Nat) (ha : 0 < a) :
    allowance a (100 * (incomeLimit + 2 * a - 1)) = 1 ∧ allowance a (100 * (incomeLimit + 2 * a)) = 0 := by
  unfold allowance excess incomeLimit
  omega

/-- The same for every tax year from 2010-11 to 2030-31, from the amount the provisions give that year: £1 at £1
below the nil point (£125,139 today), nil at it (£125,140). -/
theorem whole_pound_nil_points :
    (List.range 21).all (fun i => match amountFor (2010 + i) with
      | some a => allowanceFor (2010 + i) (100 * (incomeLimit + 2 * a - 1)) == some 1 &&
          allowanceFor (2010 + i) (100 * (incomeLimit + 2 * a)) == some 0
      | none => false) = true := by decide

/-- FA 2009's Explanatory Notes: "in 2010-11 an individual with an adjusted net income of £100,002 will have their
personal allowance reduced by £1". At £100,001 the allowance is still the full £6,475. -/
theorem fa2009_notes_example :
    allowanceFor 2010 (100 * 100001) = some 6475 ∧ allowanceFor 2010 (100 * 100002) = some 6474 := by decide

/-- In 2026-27 an odd pound in the band costs 40p of tax: the allowance does not move, so only the pound itself is
taxed, at 40%. -/
theorem odd_pound_costs_40p (k : Nat) (h : 2 * k + 2 ≤ 2 * paToday) :
    tax2026 (100 * (incomeLimit + 2 * k + 1)) = tax2026 (100 * (incomeLimit + 2 * k)) + 40 := by
  have b0 := taper_band_is_higher_rate (100 * (incomeLimit + 2 * k)) (by omega) (by unfold higherLimit; omega)
  have b1 := taper_band_is_higher_rate (100 * (incomeLimit + 2 * k + 1)) (by omega) (by unfold higherLimit; omega)
  have st := whole_pound_step paToday k h
  have e0 := whole_pound_even paToday k (by omega)
  unfold tax2026
  rw [bandTax_higher _ b1.1 b1.2, bandTax_higher _ b0.1 b0.2]
  unfold taxable
  rw [st.1, e0]
  unfold basicLimit paToday incomeLimit
  omega

/-- ... and the even pound after it costs 80p: the pound itself and the £1 of allowance it takes away, both at 40%. So
every £2 in the band costs £1.20, 60p a pound. -/
theorem even_pound_costs_80p (k : Nat) (h : 2 * k + 2 ≤ 2 * paToday) :
    tax2026 (100 * (incomeLimit + 2 * k + 2)) = tax2026 (100 * (incomeLimit + 2 * k + 1)) + 80 := by
  have b1 := taper_band_is_higher_rate (100 * (incomeLimit + 2 * k + 1)) (by omega) (by unfold higherLimit; omega)
  have b2 := taper_band_is_higher_rate (100 * (incomeLimit + 2 * k + 2)) (by omega) (by unfold higherLimit; omega)
  have st := whole_pound_step paToday k h
  have e0 := whole_pound_even paToday k (by omega)
  unfold tax2026
  rw [bandTax_higher _ b2.1 b2.2, bandTax_higher _ b1.1 b1.2]
  unfold taxable
  unfold basicLimit paToday incomeLimit at *
  omega

/-- The first two pounds over £100,000 in 2026-27: £27,432.40 of tax at £100,001 (allowance £12,570) and £27,433.20
at £100,002 (allowance £12,569). -/
theorem first_two_pounds_2026 :
    allowanceFor 2026 (100 * 100001) = some 12570 ∧ tax2026 (100 * 100001) = 2743240 ∧
      allowanceFor 2026 (100 * 100002) = some 12569 ∧ tax2026 (100 * 100002) = 2743320 := by decide

/-! ## Worked examples -/

/-- GOV.UK's adjusted net income example: £105,000. The page stops before the allowance; s35 gives £10,070. -/
theorem govuk_ani_example : allowanceFor 2026 (100 * 105000) = some 10070 := by decide

/-- GOV.UK: "your allowance is zero if your income is £125,140 or above". -/
theorem govuk_zero_at_125140 : allowanceFor 2026 (100 * 125140) = some 0 := by decide

/-- £100,000 in 2026-27: full allowance, tax £27,432. -/
theorem tax_at_100k : allowanceFor 2026 (100 * 100000) = some 12570 ∧ tax2026 (100 * 100000) = 2743200 := by
  decide

/-- £110,000 in 2026-27: allowance £7,570, tax £33,432, £6,000 more for £10,000 more income. -/
theorem tax_at_110k : allowanceFor 2026 (100 * 110000) = some 7570 ∧ tax2026 (100 * 110000) = 3343200 := by
  decide

/-- £150,000 in 2026-27: no allowance, tax £53,703. -/
theorem tax_at_150k : allowanceFor 2026 (100 * 150000) = some 0 ∧ tax2026 (100 * 150000) = 5370300 := by decide

end PersonalAllowance
