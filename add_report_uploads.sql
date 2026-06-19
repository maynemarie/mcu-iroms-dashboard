-- ============================================================
-- Add a table to track uploaded grant reports + create a Supabase
-- Storage bucket for the actual files.
-- Run once in Supabase SQL Editor.
-- ============================================================

-- 1. Table to track upload metadata
create table if not exists grant_report_uploads (
  id            bigserial primary key,
  grant_id      text not null,
  pi            text not null,
  report_type   text not null,            -- 'Mid-Project' or 'Final'
  filename      text not null,
  storage_path  text not null,            -- path in the bucket
  notes         text,
  uploaded_at   timestamptz not null default now()
);
create index if not exists grant_report_uploads_grant_idx
  on grant_report_uploads(grant_id);
create index if not exists grant_report_uploads_when_idx
  on grant_report_uploads(uploaded_at desc);

-- 2. Disable RLS on this table for the prototype
alter table grant_report_uploads disable row level security;

-- 3. Create the Storage bucket for the actual Word files
insert into storage.buckets (id, name, public)
values ('grant-reports', 'grant-reports', true)
on conflict (id) do nothing;

-- 4. Allow public uploads to this bucket (prototype)
-- Production should restrict by authenticated user with MCU email.
create policy if not exists "Public upload to grant-reports"
  on storage.objects for insert
  with check (bucket_id = 'grant-reports');

create policy if not exists "Public read from grant-reports"
  on storage.objects for select
  using (bucket_id = 'grant-reports');
