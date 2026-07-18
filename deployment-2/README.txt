STOCK & STIR — DEPLOYMENT 2

Production base expected:
  774174a Correct pantry skillet orchestration

This bundle contains two ordered commits:
  0001 Share kitchens across devices with Supabase
  0002 Add launch pantry coverage and recipe reporting

Recommended Windows commands from C:\Users\tlove\OneDrive\Desktop\SNS:

  git status --short
  git apply --check backups\deployment-2\0001-Share-kitchens-across-devices-with-Supabase.patch
  git apply backups\deployment-2\0001-Share-kitchens-across-devices-with-Supabase.patch
  git add -A
  git commit -m "Share kitchens across devices with Supabase"

  git apply --check backups\deployment-2\0002-Add-launch-pantry-coverage-and-recipe-reporting.patch
  git apply backups\deployment-2\0002-Add-launch-pantry-coverage-and-recipe-reporting.patch
  git add -A
  git commit -m "Add launch pantry coverage and recipe reporting"

  git push origin main

If Deployment 1 is already committed, skip the first patch and apply only 0002.
Use git apply, not git am. The Supabase schema migrations have already been
applied to project pbsrcqscssumywjhgino.

Verification performed:
  206 tests passed
  730 catalog subtests passed
  139/139 regional sample foods resolve and have trained behavior
  SQLite integrity check: ok
  Supabase security advisor: no findings
