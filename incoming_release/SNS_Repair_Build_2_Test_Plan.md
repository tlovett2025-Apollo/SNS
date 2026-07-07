# Stock & Stir (SNS)

# Repair Build 2 Test Plan

**Build:** v5 Beta 2D - Repair Build 2\
**Tester:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\
**Date:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-01 --- Smoke Test

**Steps** 1. Open CMD in the SNS folder. 2. Run: `python smoke_test.py`

**Expected Result** Smoke test passes.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-02 --- Version Banner

**Steps** 1. Start the app. 2. Look under the Stock & Stir title.

**Expected Result** Version shows: `v5 Beta 2D - Repair Build 2`

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-03 --- Admin Selected Row Loads Correctly

**Steps** 1. Go to **Admin Editor**. 2. Select table: `proteins`. 3.
Select **Ground Beef** (or another known row). 4. Review the edit form.

**Expected Result** The edit form loads the same record selected in the
table.

**Fail Condition** Selecting Ground Beef loads Chicken Breast or another
row.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-04 --- Protein Edit / Save / Reload

**Steps** 1. Go to **Components → Protein**. 2. Select an existing
protein. 3. Change cost level, energy level, prep, or notes. 4. Save. 5.
Reopen the same protein.

**Expected Result** Changes are saved and reload correctly.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-05 --- Vegetable Edit / Save / Reload

**Steps** 1. Go to **Components → Vegetable**. 2. Select an existing
vegetable. 3. Change common prep, soft texture, cooks fast, or notes. 4.
Save. 5. Reopen the same vegetable.

**Expected Result** Changes are saved and reload correctly.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-06 --- Foundation Edit / Save / Reload

**Steps** 1. Go to **Components → Foundation**. 2. Select an existing
foundation. 3. Change foundation type, texture, pantry style, energy,
gravy/sauce flags, or notes. 4. Save. 5. Reopen the same foundation.

**Expected Result** Changes are saved and reload correctly.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-07 --- Ingredient State Edit

**Steps** 1. Go to **Components → Ingredient State**. 2. Select an
existing state. 3. Change state, storage, energy, prep minutes, cook
minutes, or notes. 4. Save and reopen.

**Expected Result** Ingredient State updates persist.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-08 --- Ingredient Alias Edit

**Steps** 1. Go to **Components → Ingredient Alias**. 2. Select an
existing alias. 3. Change alias name, alias type, or notes. 4. Save and
reopen.

**Expected Result** Alias updates persist.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-09 --- Equipment Edit

**Steps** 1. Go to **Components → Equipment**. 2. Select existing
equipment. 3. Change equipment type or notes. 4. Save and reopen.

**Expected Result** Equipment updates persist.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-10 --- Sauce Edit

**Steps** 1. Go to **Components → Sauce**. 2. Select existing sauce. 3.
Change sauce family, dairy status, energy, or notes. 4. Save and reopen.

**Expected Result** Sauce updates persist.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-11 --- Duplicate Foundation Protection

**Steps** 1. Try to add `Test_Foundation`. 2. Try to add
`test_foundation`.

**Expected Result** The second entry is rejected as a duplicate.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

## TC-RB2-12 --- Human Names Instead of Raw IDs

**Steps** 1. Review proteins, vegetables, states, aliases, and Admin
Editor linked fields.

**Expected Result** Readable names are displayed wherever practical
instead of numeric IDs.

**Pass / Fail:** ☐ Pass ☐ Fail

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

------------------------------------------------------------------------

# Final Decision

☐ PASS --- Ready for Ingredient Wave 1

☐ FAIL --- Repair Build 3 Required

## Overall Notes

------------------------------------------------------------------------

------------------------------------------------------------------------

------------------------------------------------------------------------
