-- Phase 5: profiles table + signup trigger
-- Apply in Supabase SQL Editor

-- Profiles table
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  auth_provider text not null default 'anonymous',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Users can read and update their own profile
create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id);

create policy "profiles_insert_own"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Auto-create profile on signup (anonymous or Google)
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  provider text;
  name text;
  avatar text;
begin
  provider := coalesce(
    new.raw_app_meta_data->>'provider',
    (select identity_data->>'provider' from auth.identities where user_id = new.id limit 1),
    'anonymous'
  );

  if new.is_anonymous then
    provider := 'anonymous';
  end if;

  name := coalesce(
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'name',
    case when new.is_anonymous then 'ضيف' else new.email end
  );

  avatar := coalesce(
    new.raw_user_meta_data->>'avatar_url',
    new.raw_user_meta_data->>'picture'
  );

  insert into public.profiles (id, display_name, avatar_url, auth_provider)
  values (new.id, name, avatar, provider)
  on conflict (id) do update set
    display_name = excluded.display_name,
    avatar_url = excluded.avatar_url,
    auth_provider = excluded.auth_provider,
    updated_at = now();

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Update profile when user links Google (identity change)
create or replace function public.handle_user_updated()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  provider text;
begin
  if old.is_anonymous = true and new.is_anonymous = false then
    provider := coalesce(new.raw_app_meta_data->>'provider', 'google');
    update public.profiles
    set
      auth_provider = provider,
      display_name = coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', display_name),
      avatar_url = coalesce(new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture', avatar_url),
      updated_at = now()
    where id = new.id;
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_updated on auth.users;

create trigger on_auth_user_updated
  after update on auth.users
  for each row execute function public.handle_user_updated();
