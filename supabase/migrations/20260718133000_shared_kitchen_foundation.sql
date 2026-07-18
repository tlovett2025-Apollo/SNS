-- Stock & Stir Deployment 1: durable household source of truth.
-- Culinary knowledge remains in the versioned CKB SQLite database. These
-- tables contain user-owned identity, kitchen, preference, and feedback data.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  default_servings integer not null default 4 check (default_servings between 1 and 30),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table public.households (
  household_id uuid primary key default gen_random_uuid(),
  household_name text not null default 'My Kitchen',
  created_by_user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table public.household_members (
  household_id uuid not null references public.households(household_id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'member')),
  joined_at timestamptz not null default timezone('utc', now()),
  primary key (household_id, user_id)
);

create or replace function public.is_household_member(target_household_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.household_members
    where household_id = target_household_id and user_id = auth.uid()
  );
$$;

create or replace function public.is_household_owner(target_household_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.household_members
    where household_id = target_household_id
      and user_id = auth.uid()
      and role = 'owner'
  );
$$;

create table public.household_people (
  person_id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(household_id) on delete cascade,
  linked_user_id uuid references auth.users(id) on delete set null,
  display_name text not null,
  appetite text not null default 'standard' check (appetite in ('light', 'standard', 'big')),
  active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table public.inventory_lots (
  inventory_lot_id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(household_id) on delete cascade,
  canonical_name text not null,
  form_name text not null default '',
  storage_location text not null check (storage_location in ('Pantry', 'Fridge', 'Freezer', 'Fresh')),
  quantity numeric not null default 0 check (quantity >= 0),
  unit text not null default 'item',
  quantity_band text check (quantity_band is null or quantity_band in ('a_little', 'some', 'plenty')),
  expiration_date date,
  confidence_level text not null default 'user_selected',
  origin text not null default 'manual',
  opened_at date,
  refrigerated_after_opening boolean,
  package_weight_oz numeric check (package_weight_oz is null or package_weight_oz > 0),
  client_item_id text,
  version bigint not null default 1 check (version > 0),
  is_deleted boolean not null default false,
  updated_by_user_id uuid not null references auth.users(id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (household_id, client_item_id)
);

create index inventory_lots_household_updated_idx
  on public.inventory_lots (household_id, updated_at);
create index inventory_lots_household_name_idx
  on public.inventory_lots (household_id, lower(canonical_name));

create table public.household_equipment (
  equipment_id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(household_id) on delete cascade,
  equipment_name text not null,
  available boolean not null default true,
  details jsonb not null default '{}'::jsonb,
  updated_by_user_id uuid not null references auth.users(id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);
create unique index household_equipment_name_idx
  on public.household_equipment (household_id, lower(equipment_name));

create table public.household_preferences (
  preference_id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(household_id) on delete cascade,
  person_id uuid references public.household_people(person_id) on delete cascade,
  preference_type text not null check (preference_type in (
    'allergy', 'medical_exclusion', 'religious_exclusion', 'exclusion',
    'dislike', 'preference', 'default'
  )),
  target_type text not null check (target_type in (
    'ingredient', 'ingredient_family', 'cuisine', 'method', 'form', 'setting'
  )),
  target_value text not null,
  severity text not null default 'avoid' check (severity in ('never', 'avoid', 'dislike', 'prefer')),
  notes text not null default '',
  active boolean not null default true,
  updated_by_user_id uuid not null references auth.users(id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);
create index household_preferences_household_idx
  on public.household_preferences (household_id, active, preference_type);

create table public.kitchen_imports (
  import_id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(household_id) on delete cascade,
  submitted_by_user_id uuid not null references auth.users(id),
  source_type text not null check (source_type in ('browser_migration', 'csv', 'sample_pantry', 'barcode', 'photo')),
  import_mode text not null check (import_mode in ('merge', 'replace', 'draft')),
  source_fingerprint text,
  imported_count integer not null default 0 check (imported_count >= 0),
  rejected_count integer not null default 0 check (rejected_count >= 0),
  created_at timestamptz not null default timezone('utc', now()),
  unique (household_id, source_type, source_fingerprint)
);

create table public.recipe_reports (
  report_id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(household_id) on delete cascade,
  submitted_by_user_id uuid not null references auth.users(id),
  candidate_id text,
  build_id text,
  commit_id text,
  page_source text not null default '',
  recipe_snapshot jsonb not null,
  rendered_recipe_text text not null,
  user_note text not null default '',
  status text not null default 'new' check (status in (
    'new', 'confirmed_problem', 'needs_information', 'training_required',
    'engine_defect', 'fixed', 'valid_needs_clarity', 'cannot_reproduce'
  )),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);
create index recipe_reports_status_idx on public.recipe_reports (status, created_at);

create or replace function public.add_household_owner()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.household_members (household_id, user_id, role)
  values (new.household_id, new.created_by_user_id, 'owner')
  on conflict do nothing;
  return new;
end;
$$;

create trigger households_add_owner
after insert on public.households
for each row execute function public.add_household_owner();

create or replace function public.create_new_user_kitchen()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  chosen_name text;
begin
  chosen_name := coalesce(
    nullif(trim(new.raw_user_meta_data ->> 'display_name'), ''),
    nullif(split_part(coalesce(new.email, ''), '@', 1), ''),
    'Cook'
  );
  insert into public.profiles (user_id, display_name)
  values (new.id, chosen_name)
  on conflict (user_id) do nothing;
  insert into public.households (household_name, created_by_user_id)
  values ('My Kitchen', new.id);
  return new;
end;
$$;

create trigger auth_user_creates_kitchen
after insert on auth.users
for each row execute function public.create_new_user_kitchen();

create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();
create trigger households_set_updated_at before update on public.households
for each row execute function public.set_updated_at();
create trigger household_people_set_updated_at before update on public.household_people
for each row execute function public.set_updated_at();
create trigger inventory_lots_set_updated_at before update on public.inventory_lots
for each row execute function public.set_updated_at();
create trigger household_equipment_set_updated_at before update on public.household_equipment
for each row execute function public.set_updated_at();
create trigger household_preferences_set_updated_at before update on public.household_preferences
for each row execute function public.set_updated_at();
create trigger recipe_reports_set_updated_at before update on public.recipe_reports
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.households enable row level security;
alter table public.household_members enable row level security;
alter table public.household_people enable row level security;
alter table public.inventory_lots enable row level security;
alter table public.household_equipment enable row level security;
alter table public.household_preferences enable row level security;
alter table public.kitchen_imports enable row level security;
alter table public.recipe_reports enable row level security;

create policy profiles_select_own on public.profiles
for select using (user_id = auth.uid());
create policy profiles_insert_own on public.profiles
for insert with check (user_id = auth.uid());
create policy profiles_update_own on public.profiles
for update using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy households_select_member on public.households
for select using (public.is_household_member(household_id));
create policy households_insert_self on public.households
for insert with check (created_by_user_id = auth.uid());
create policy households_update_owner on public.households
for update using (public.is_household_owner(household_id));
create policy households_delete_owner on public.households
for delete using (public.is_household_owner(household_id));

create policy household_members_select_member on public.household_members
for select using (public.is_household_member(household_id));
create policy household_members_insert_owner on public.household_members
for insert with check (public.is_household_owner(household_id));
create policy household_members_update_owner on public.household_members
for update using (public.is_household_owner(household_id));
create policy household_members_delete_owner on public.household_members
for delete using (public.is_household_owner(household_id));

create policy household_people_member_all on public.household_people
for all using (public.is_household_member(household_id))
with check (public.is_household_member(household_id));
create policy inventory_lots_member_all on public.inventory_lots
for all using (public.is_household_member(household_id))
with check (public.is_household_member(household_id) and updated_by_user_id = auth.uid());
create policy household_equipment_member_all on public.household_equipment
for all using (public.is_household_member(household_id))
with check (public.is_household_member(household_id) and updated_by_user_id = auth.uid());
create policy household_preferences_member_all on public.household_preferences
for all using (public.is_household_member(household_id))
with check (public.is_household_member(household_id) and updated_by_user_id = auth.uid());
create policy kitchen_imports_member_insert on public.kitchen_imports
for insert with check (
  public.is_household_member(household_id) and submitted_by_user_id = auth.uid()
);
create policy kitchen_imports_member_select on public.kitchen_imports
for select using (public.is_household_member(household_id));
create policy recipe_reports_submit on public.recipe_reports
for insert with check (
  public.is_household_member(household_id) and submitted_by_user_id = auth.uid()
);
create policy recipe_reports_read_own on public.recipe_reports
for select using (submitted_by_user_id = auth.uid());

-- Backfill safely if the project acquired an Auth user before this migration.
insert into public.profiles (user_id, display_name)
select id, coalesce(nullif(split_part(coalesce(email, ''), '@', 1), ''), 'Cook')
from auth.users
on conflict (user_id) do nothing;

insert into public.households (household_name, created_by_user_id)
select 'My Kitchen', user_id
from public.profiles profile
where not exists (
  select 1 from public.households household
  where household.created_by_user_id = profile.user_id
);
