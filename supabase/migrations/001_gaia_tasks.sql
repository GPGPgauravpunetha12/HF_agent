-- GAIA agent: task metadata + file references
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- Storage bucket (create in Dashboard > Storage if this fails)
insert into storage.buckets (id, name, public)
values ('gaia-files', 'gaia-files', true)
on conflict (id) do nothing;

-- Task runs and file metadata
create table if not exists public.gaia_tasks (
  id uuid primary key default gen_random_uuid(),
  task_id text not null unique,
  question text,
  file_name text,
  storage_path text,
  public_url text,
  analysis_preview text,
  answer text,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists gaia_tasks_status_idx on public.gaia_tasks (status);
create index if not exists gaia_tasks_created_at_idx on public.gaia_tasks (created_at desc);

alter table public.gaia_tasks enable row level security;

-- Agent uses publishable key: allow read/write for anon (tighten for production)
create policy "gaia_tasks_anon_select"
  on public.gaia_tasks for select
  to anon
  using (true);

create policy "gaia_tasks_anon_insert"
  on public.gaia_tasks for insert
  to anon
  with check (true);

create policy "gaia_tasks_anon_update"
  on public.gaia_tasks for update
  to anon
  using (true)
  with check (true);

-- Storage: allow uploads and reads for gaia-files bucket
create policy "gaia_files_public_read"
  on storage.objects for select
  to anon
  using (bucket_id = 'gaia-files');

create policy "gaia_files_anon_insert"
  on storage.objects for insert
  to anon
  with check (bucket_id = 'gaia-files');

create policy "gaia_files_anon_update"
  on storage.objects for update
  to anon
  using (bucket_id = 'gaia-files')
  with check (bucket_id = 'gaia-files');

grant select, insert, update on public.gaia_tasks to anon;
