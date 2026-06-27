-- Phase 7: summaries table + RLS
-- Apply in Supabase SQL Editor (after 002_documents.sql)

-- Summaries table
create table if not exists public.summaries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
  original_text text not null,
  summary_text text not null,
  word_count integer,
  compression_ratio real,
  created_at timestamptz not null default now()
);

-- Index for user summary listing (loadSummaries queries by user_id + order by created_at)
create index if not exists idx_summaries_user_id on public.summaries(user_id, created_at desc);

alter table public.summaries enable row level security;

create policy "summaries_select_own"
  on public.summaries for select
  using (auth.uid() = user_id);

create policy "summaries_insert_own"
  on public.summaries for insert
  with check (auth.uid() = user_id);

create policy "summaries_delete_own"
  on public.summaries for delete
  using (auth.uid() = user_id);
