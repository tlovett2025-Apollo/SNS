-- Make whole-kitchen replacement idempotent after alias canonicalization.
-- Equal ingredient states are coalesced before insert, and the server-owned
-- client_item_id includes the full state identity rather than only name/form/
-- storage.  This closes the regional-pantry duplicate-key failure without
-- weakening household isolation or the existing unique constraint.

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
  with normalized_inventory as (
    select
      trim(item ->> 'name') as canonical_name,
      coalesce(nullif(trim(coalesce(item ->> 'form', item ->> 'form_name', '')), ''), 'On hand') as form_name,
      case lower(coalesce(item ->> 'storage', item ->> 'storage_location', 'pantry'))
        when 'fridge' then 'Fridge'
        when 'freezer' then 'Freezer'
        when 'fresh' then 'Fresh'
        else 'Pantry'
      end as storage_location,
      greatest(0, coalesce((item ->> 'quantity')::numeric, 0)) as quantity,
      coalesce(nullif(trim(item ->> 'unit'), ''), 'item') as unit,
      nullif(item ->> 'expiration_date', '')::date as expiration_date,
      nullif(item ->> 'opened_at', '')::date as opened_at,
      nullif(item ->> 'refrigerated_after_opening', '')::boolean as refrigerated_after_opening,
      nullif(item ->> 'package_weight_oz', '')::numeric as package_weight_oz,
      coalesce(nullif(item ->> 'origin', ''), 'account_sync') as origin
    from jsonb_array_elements(v_inventory) item
    where trim(coalesce(item ->> 'name', '')) <> ''
      and coalesce((item ->> 'quantity')::numeric, 0) > 0
  ),
  coalesced_inventory as (
    select
      canonical_name, form_name, storage_location, sum(quantity) as quantity,
      unit, expiration_date, opened_at, refrigerated_after_opening,
      package_weight_oz, min(origin) as origin
    from normalized_inventory
    group by
      canonical_name, form_name, storage_location, unit, expiration_date,
      opened_at, refrigerated_after_opening, package_weight_oz
  )
  insert into public.inventory_lots (
    household_id, canonical_name, form_name, storage_location, quantity, unit,
    expiration_date, opened_at, refrigerated_after_opening, package_weight_oz,
    client_item_id, origin, updated_by_user_id
  )
  select
    v_household_id,
    canonical_name,
    form_name,
    storage_location,
    quantity,
    unit,
    expiration_date,
    opened_at,
    refrigerated_after_opening,
    package_weight_oz,
    md5(
      lower(canonical_name) || '|' || lower(storage_location) || '|' ||
      lower(form_name) || '|' || lower(unit) || '|' ||
      coalesce(expiration_date::text, '') || '|' ||
      coalesce(opened_at::text, '') || '|' ||
      coalesce(refrigerated_after_opening::text, '') || '|' ||
      coalesce(package_weight_oz::text, '')
    ),
    origin,
    v_user_id
  from coalesced_inventory;

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

revoke all on function public.sync_my_kitchen(jsonb, text, text) from public, anon;
grant execute on function public.sync_my_kitchen(jsonb, text, text) to authenticated;
