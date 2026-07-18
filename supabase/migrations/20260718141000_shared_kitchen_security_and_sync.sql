-- Harden Deployment 1 and expose two user-scoped RPCs for the static site.

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create or replace function private.is_household_member(target_household_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.household_members
    where household_id = target_household_id
      and user_id = (select auth.uid())
  );
$$;

create or replace function private.is_household_owner(target_household_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.household_members
    where household_id = target_household_id
      and user_id = (select auth.uid())
      and role = 'owner'
  );
$$;

revoke all on function private.is_household_member(uuid) from public, anon;
revoke all on function private.is_household_owner(uuid) from public, anon;
grant execute on function private.is_household_member(uuid) to authenticated;
grant execute on function private.is_household_owner(uuid) to authenticated;

-- Trigger functions are never client RPCs.
revoke all on function public.add_household_owner() from public, anon, authenticated;
revoke all on function public.create_new_user_kitchen() from public, anon, authenticated;
revoke all on function public.set_updated_at() from public, anon, authenticated;

drop policy if exists profiles_select_own on public.profiles;
drop policy if exists profiles_insert_own on public.profiles;
drop policy if exists profiles_update_own on public.profiles;
drop policy if exists households_select_member on public.households;
drop policy if exists households_insert_self on public.households;
drop policy if exists households_update_owner on public.households;
drop policy if exists households_delete_owner on public.households;
drop policy if exists household_members_select_member on public.household_members;
drop policy if exists household_members_insert_owner on public.household_members;
drop policy if exists household_members_update_owner on public.household_members;
drop policy if exists household_members_delete_owner on public.household_members;
drop policy if exists household_people_member_all on public.household_people;
drop policy if exists inventory_lots_member_all on public.inventory_lots;
drop policy if exists household_equipment_member_all on public.household_equipment;
drop policy if exists household_preferences_member_all on public.household_preferences;
drop policy if exists kitchen_imports_member_insert on public.kitchen_imports;
drop policy if exists kitchen_imports_member_select on public.kitchen_imports;
drop policy if exists recipe_reports_submit on public.recipe_reports;
drop policy if exists recipe_reports_read_own on public.recipe_reports;

create policy profiles_select_own on public.profiles
for select to authenticated using (user_id = (select auth.uid()));
create policy profiles_insert_own on public.profiles
for insert to authenticated with check (user_id = (select auth.uid()));
create policy profiles_update_own on public.profiles
for update to authenticated using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy households_select_member on public.households
for select to authenticated using (private.is_household_member(household_id));
create policy households_insert_self on public.households
for insert to authenticated with check (created_by_user_id = (select auth.uid()));
create policy households_update_owner on public.households
for update to authenticated using (private.is_household_owner(household_id))
with check (private.is_household_owner(household_id));
create policy households_delete_owner on public.households
for delete to authenticated using (private.is_household_owner(household_id));

create policy household_members_select_member on public.household_members
for select to authenticated using (private.is_household_member(household_id));
create policy household_members_insert_owner on public.household_members
for insert to authenticated with check (private.is_household_owner(household_id));
create policy household_members_update_owner on public.household_members
for update to authenticated using (private.is_household_owner(household_id))
with check (private.is_household_owner(household_id));
create policy household_members_delete_owner on public.household_members
for delete to authenticated using (private.is_household_owner(household_id));

create policy household_people_member_all on public.household_people
for all to authenticated using (private.is_household_member(household_id))
with check (private.is_household_member(household_id));
create policy inventory_lots_member_all on public.inventory_lots
for all to authenticated using (private.is_household_member(household_id))
with check (
  private.is_household_member(household_id)
  and updated_by_user_id = (select auth.uid())
);
create policy household_equipment_member_all on public.household_equipment
for all to authenticated using (private.is_household_member(household_id))
with check (
  private.is_household_member(household_id)
  and updated_by_user_id = (select auth.uid())
);
create policy household_preferences_member_all on public.household_preferences
for all to authenticated using (private.is_household_member(household_id))
with check (
  private.is_household_member(household_id)
  and updated_by_user_id = (select auth.uid())
);
create policy kitchen_imports_member_insert on public.kitchen_imports
for insert to authenticated with check (
  private.is_household_member(household_id)
  and submitted_by_user_id = (select auth.uid())
);
create policy kitchen_imports_member_select on public.kitchen_imports
for select to authenticated using (private.is_household_member(household_id));
create policy recipe_reports_submit on public.recipe_reports
for insert to authenticated with check (
  private.is_household_member(household_id)
  and submitted_by_user_id = (select auth.uid())
);
create policy recipe_reports_read_own on public.recipe_reports
for select to authenticated using (submitted_by_user_id = (select auth.uid()));

alter table public.profiles
  add column if not exists default_energy text not null default 'Low'
    check (default_energy in ('Very Low', 'Low', 'Medium', 'High'));
alter table public.household_preferences
  add column if not exists preference_value jsonb not null default '{}'::jsonb;

create index if not exists households_created_by_idx
  on public.households (created_by_user_id);
create index if not exists household_members_user_idx
  on public.household_members (user_id, household_id);
create index if not exists household_people_household_idx
  on public.household_people (household_id);
create index if not exists household_people_linked_user_idx
  on public.household_people (linked_user_id) where linked_user_id is not null;
create index if not exists inventory_lots_updated_by_idx
  on public.inventory_lots (updated_by_user_id);
create index if not exists household_equipment_updated_by_idx
  on public.household_equipment (updated_by_user_id);
create index if not exists household_preferences_person_idx
  on public.household_preferences (person_id) where person_id is not null;
create index if not exists household_preferences_updated_by_idx
  on public.household_preferences (updated_by_user_id);
create index if not exists kitchen_imports_submitted_by_idx
  on public.kitchen_imports (submitted_by_user_id);
create index if not exists recipe_reports_household_idx
  on public.recipe_reports (household_id);
create index if not exists recipe_reports_submitted_by_idx
  on public.recipe_reports (submitted_by_user_id);

grant select, insert, update, delete on table public.profiles to authenticated;
grant select, insert, update, delete on table public.households to authenticated;
grant select, insert, update, delete on table public.household_members to authenticated;
grant select, insert, update, delete on table public.household_people to authenticated;
grant select, insert, update, delete on table public.inventory_lots to authenticated;
grant select, insert, update, delete on table public.household_equipment to authenticated;
grant select, insert, update, delete on table public.household_preferences to authenticated;
grant select, insert on table public.kitchen_imports to authenticated;
grant select, insert on table public.recipe_reports to authenticated;

drop function if exists public.is_household_member(uuid);
drop function if exists public.is_household_owner(uuid);

create or replace function public.my_kitchen_snapshot()
returns jsonb
language plpgsql
stable
security invoker
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_household_id uuid;
  v_profile public.profiles%rowtype;
begin
  if v_user_id is null then
    raise exception 'Authentication is required.' using errcode = '42501';
  end if;

  select household_id into v_household_id
  from public.household_members
  where user_id = v_user_id
  order by (role = 'owner') desc, joined_at
  limit 1;

  if v_household_id is null then
    raise exception 'No kitchen is attached to this account.' using errcode = '42501';
  end if;

  select * into v_profile from public.profiles where user_id = v_user_id;

  return jsonb_build_object(
    'household_id', v_household_id,
    'servings', coalesce(v_profile.default_servings, 4),
    'energy', coalesce(v_profile.default_energy, 'Low'),
    'effort', coalesce(v_profile.default_energy, 'Low'),
    'tonight_effort', coalesce(v_profile.default_energy, 'Low'),
    'foods', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', inventory_lot_id,
        'name', canonical_name,
        'form', form_name,
        'storage', storage_location,
        'quantity', quantity,
        'unit', unit,
        'opened_at', opened_at,
        'refrigerated_after_opening', refrigerated_after_opening,
        'package_weight_oz', package_weight_oz,
        'expiration_date', expiration_date,
        'custom', true
      ) order by storage_location, canonical_name)
      from public.inventory_lots
      where household_id = v_household_id and not is_deleted and quantity > 0
    ), '[]'::jsonb),
    'inventory', coalesce((
      select jsonb_agg(jsonb_build_object(
        'name', canonical_name,
        'form', form_name,
        'storage', storage_location,
        'quantity', quantity,
        'unit', unit,
        'opened_at', opened_at,
        'refrigerated_after_opening', refrigerated_after_opening,
        'package_weight_oz', package_weight_oz,
        'expiration_date', expiration_date
      ) order by storage_location, canonical_name)
      from public.inventory_lots
      where household_id = v_household_id and not is_deleted and quantity > 0
    ), '[]'::jsonb),
    'equipment', coalesce((
      select jsonb_agg(jsonb_build_object(
        'name', equipment_name,
        'active', available,
        'available', available,
        'custom', true
      ) order by equipment_name)
      from public.household_equipment
      where household_id = v_household_id
    ), '[]'::jsonb),
    'household_members', coalesce((
      select jsonb_agg(jsonb_build_object(
        'name', display_name,
        'appetite', appetite
      ) order by created_at)
      from public.household_people
      where household_id = v_household_id and active
    ), '[]'::jsonb),
    'preferences', coalesce((
      select jsonb_agg(jsonb_build_object(
        'preference_type', preference_type,
        'target_type', target_type,
        'target_value', target_value,
        'severity', severity,
        'notes', notes,
        'value', preference_value
      ) order by created_at)
      from public.household_preferences
      where household_id = v_household_id and active
    ), '[]'::jsonb)
  );
end;
$$;

create or replace function public.sync_my_kitchen(
  p_snapshot jsonb,
  p_source_type text default null,
  p_source_fingerprint text default null
)
returns jsonb
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_household_id uuid;
  v_inventory jsonb := coalesce(p_snapshot -> 'inventory', p_snapshot -> 'foods', '[]'::jsonb);
  v_equipment jsonb := coalesce(p_snapshot -> 'equipment', '[]'::jsonb);
  v_people jsonb := coalesce(
    p_snapshot -> 'household_members',
    p_snapshot #> '{meal_preferences,household_members}',
    '[]'::jsonb
  );
  v_preferences jsonb := coalesce(p_snapshot -> 'preferences', '[]'::jsonb);
begin
  if v_user_id is null then
    raise exception 'Authentication is required.' using errcode = '42501';
  end if;

  select household_id into v_household_id
  from public.household_members
  where user_id = v_user_id
  order by (role = 'owner') desc, joined_at
  limit 1;

  if v_household_id is null then
    raise exception 'No kitchen is attached to this account.' using errcode = '42501';
  end if;

  update public.profiles
  set default_servings = greatest(1, least(30, coalesce((p_snapshot ->> 'servings')::integer, default_servings))),
      default_energy = case
        when coalesce(p_snapshot ->> 'effort', p_snapshot ->> 'energy', p_snapshot ->> 'tonight_effort')
          in ('Very Low', 'Low', 'Medium', 'High')
        then coalesce(p_snapshot ->> 'effort', p_snapshot ->> 'energy', p_snapshot ->> 'tonight_effort')
        else default_energy
      end
  where user_id = v_user_id;

  delete from public.inventory_lots where household_id = v_household_id;
  insert into public.inventory_lots (
    household_id, canonical_name, form_name, storage_location, quantity, unit,
    expiration_date, opened_at, refrigerated_after_opening, package_weight_oz,
    client_item_id, origin, updated_by_user_id
  )
  select
    v_household_id,
    trim(item ->> 'name'),
    coalesce(nullif(trim(coalesce(item ->> 'form', item ->> 'form_name', '')), ''), 'On hand'),
    case lower(coalesce(item ->> 'storage', item ->> 'storage_location', 'pantry'))
      when 'fridge' then 'Fridge'
      when 'freezer' then 'Freezer'
      when 'fresh' then 'Fresh'
      else 'Pantry'
    end,
    greatest(0, coalesce((item ->> 'quantity')::numeric, 0)),
    coalesce(nullif(trim(item ->> 'unit'), ''), 'item'),
    nullif(item ->> 'expiration_date', '')::date,
    nullif(item ->> 'opened_at', '')::date,
    nullif(item ->> 'refrigerated_after_opening', '')::boolean,
    nullif(item ->> 'package_weight_oz', '')::numeric,
    md5(lower(trim(item ->> 'name')) || '|' || lower(coalesce(item ->> 'storage', item ->> 'storage_location', 'pantry')) || '|' || lower(coalesce(item ->> 'form', item ->> 'form_name', ''))),
    coalesce(nullif(item ->> 'origin', ''), 'account_sync'),
    v_user_id
  from jsonb_array_elements(v_inventory) item
  where trim(coalesce(item ->> 'name', '')) <> ''
    and coalesce((item ->> 'quantity')::numeric, 0) > 0;

  delete from public.household_equipment where household_id = v_household_id;
  insert into public.household_equipment (
    household_id, equipment_name, available, updated_by_user_id
  )
  select
    v_household_id,
    trim(item ->> 'name'),
    coalesce((item ->> 'available')::boolean, (item ->> 'active')::boolean, true),
    v_user_id
  from jsonb_array_elements(v_equipment) item
  where trim(coalesce(item ->> 'name', '')) <> ''
    and coalesce((item ->> 'available')::boolean, (item ->> 'active')::boolean, true);

  delete from public.household_people where household_id = v_household_id;
  insert into public.household_people (household_id, display_name, appetite)
  select
    v_household_id,
    coalesce(nullif(trim(item ->> 'name'), ''), 'Household member'),
    case when item ->> 'appetite' in ('light', 'standard', 'big')
      then item ->> 'appetite' else 'standard' end
  from jsonb_array_elements(v_people) item;

  if p_snapshot ? 'preferences' then
    delete from public.household_preferences where household_id = v_household_id;
    insert into public.household_preferences (
      household_id, preference_type, target_type, target_value, severity,
      notes, preference_value, updated_by_user_id
    )
    select
      v_household_id,
      case when item ->> 'preference_type' in (
        'allergy', 'medical_exclusion', 'religious_exclusion', 'exclusion',
        'dislike', 'preference', 'default'
      ) then item ->> 'preference_type' else 'preference' end,
      case when item ->> 'target_type' in (
        'ingredient', 'ingredient_family', 'cuisine', 'method', 'form', 'setting'
      ) then item ->> 'target_type' else 'ingredient' end,
      trim(item ->> 'target_value'),
      case when item ->> 'severity' in ('never', 'avoid', 'dislike', 'prefer')
        then item ->> 'severity' else 'avoid' end,
      coalesce(item ->> 'notes', ''),
      coalesce(item -> 'value', '{}'::jsonb),
      v_user_id
    from jsonb_array_elements(v_preferences) item
    where trim(coalesce(item ->> 'target_value', '')) <> '';
  end if;

  if p_source_type in ('browser_migration', 'csv', 'sample_pantry', 'barcode', 'photo') then
    insert into public.kitchen_imports (
      household_id, submitted_by_user_id, source_type, import_mode,
      source_fingerprint, imported_count
    ) values (
      v_household_id, v_user_id, p_source_type, 'replace',
      p_source_fingerprint, jsonb_array_length(v_inventory)
    ) on conflict (household_id, source_type, source_fingerprint) do nothing;
  end if;

  return public.my_kitchen_snapshot();
end;
$$;

revoke all on function public.my_kitchen_snapshot() from public, anon;
revoke all on function public.sync_my_kitchen(jsonb, text, text) from public, anon;
grant execute on function public.my_kitchen_snapshot() to authenticated;
grant execute on function public.sync_my_kitchen(jsonb, text, text) to authenticated;
