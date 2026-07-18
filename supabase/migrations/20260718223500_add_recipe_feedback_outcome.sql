-- Record positive and negative recipe feedback without overloading the
-- report-resolution workflow status.

alter table public.recipe_reports
  add column if not exists report_outcome text not null default 'NG';

alter table public.recipe_reports
  drop constraint if exists recipe_reports_outcome_check;
alter table public.recipe_reports
  add constraint recipe_reports_outcome_check
  check (report_outcome in ('OK', 'NG'));

alter table public.recipe_reports
  drop constraint if exists recipe_reports_issue_categories_check;
alter table public.recipe_reports
  add constraint recipe_reports_issue_categories_check check (
    cardinality(issue_categories) between 1 and 6
    and issue_categories <@ array[
      'recipe_ok', 'general_review', 'wrong_ingredients',
      'weird_instructions', 'uncookable_combination',
      'timing_or_effort', 'wrong_quantity'
    ]::text[]
    and (
      (report_outcome = 'OK' and issue_categories = array['recipe_ok']::text[])
      or
      (report_outcome = 'NG' and not (issue_categories && array['recipe_ok']::text[]))
    )
  );

drop function if exists public.submit_recipe_report(
  text, text, text, jsonb, text, text, text[]
);

create function public.submit_recipe_report(
  p_candidate_id text,
  p_build_id text,
  p_commit_id text,
  p_recipe_snapshot jsonb,
  p_rendered_recipe_text text,
  p_user_note text default '',
  p_issue_categories text[] default array['general_review']::text[],
  p_report_outcome text default 'NG'
)
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_household_id uuid;
  v_report_id uuid;
begin
  if v_user_id is null then
    raise exception 'Log in to record recipe feedback.';
  end if;

  select member.household_id into v_household_id
  from public.household_members member
  where member.user_id = v_user_id
  order by member.joined_at
  limit 1;

  if v_household_id is null then
    raise exception 'No household is available for this feedback.';
  end if;

  insert into public.recipe_reports (
    household_id, submitted_by_user_id, candidate_id, build_id, commit_id,
    page_source, recipe_snapshot, rendered_recipe_text, user_note,
    issue_categories, report_outcome
  ) values (
    v_household_id, v_user_id, nullif(btrim(p_candidate_id), ''),
    nullif(btrim(p_build_id), ''), nullif(btrim(p_commit_id), ''),
    'recipe.html', p_recipe_snapshot, p_rendered_recipe_text,
    coalesce(p_user_note, ''), p_issue_categories, upper(p_report_outcome)
  )
  returning report_id into v_report_id;

  return v_report_id;
end;
$$;

revoke all on function public.submit_recipe_report(
  text, text, text, jsonb, text, text, text[], text
) from public, anon;
grant execute on function public.submit_recipe_report(
  text, text, text, jsonb, text, text, text[], text
) to authenticated;
