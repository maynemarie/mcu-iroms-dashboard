-- ============================================================
-- Submitted in-house grant documents (application forms & progress
-- reports uploaded by applicants). Run once in the Supabase SQL Editor.
-- ============================================================

create table if not exists public.in_house_grant_submissions (
    id               uuid primary key default gen_random_uuid(),
    submission_type  text        not null
                     check (submission_type in ('Application Form', 'Progress Report')),
    applicant_name   text        not null,
    applicant_email  text,
    college          text,
    project_id       text,
    project_title    text,
    doc_path         text,
    doc_filename     text,
    notes            text,
    submitted_at     timestamptz not null default now()
);

-- For installs that created the table before project_id was added:
alter table public.in_house_grant_submissions
    add column if not exists project_id text;

-- The dashboard uses the anon key (no per-user session), like the other
-- tables — so RLS must be off (or fully permissive) for inserts to work.
alter table public.in_house_grant_submissions disable row level security;

create index if not exists ih_grant_submissions_when_idx
    on public.in_house_grant_submissions (submitted_at desc);
