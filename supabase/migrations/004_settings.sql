-- Phase 7: settings table + RLS
-- Apply in Supabase SQL Editor (after 001_profiles.sql)

-- Settings table (one row per user)
create table if not exists public.settings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  theme text not null default 'dark',
  preferences jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.settings enable row level security;

create policy "settings_select_own"
  on public.settings for select
  using (auth.uid() = user_id);

create policy "settings_insert_own"
  on public.settings for insert
  with check (auth.uid() = user_id);

create policy "settings_update_own"
  on public.settings for update
  using (auth.uid() = user_id);

-- Reuse set_updated_at() trigger function from 002_documents.sql
create trigger settings_set_updated_at
  before update on public.settings
  for each row execute function public.set_updated_at();
