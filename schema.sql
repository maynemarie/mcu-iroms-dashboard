-- ============================================================
-- MCU IRO Dashboard — Supabase Postgres schema
--
-- Run this once in the Supabase SQL Editor:
--   Supabase Dashboard → SQL Editor → New query → paste this → Run
-- ============================================================

-- Cleanly drop and recreate (only for first setup — comment out on production redeploy!)
-- drop table if exists budget_entries cascade;
-- drop table if exists grant_reports cascade;
-- drop table if exists grant_projects cascade;
-- drop table if exists erb_protocols cascade;

-- ============================================================
-- 1. ERB / IRB Protocols
-- ============================================================
create table if not exists erb_protocols (
  id              bigserial primary key,
  protocol_id     text unique not null,            -- MCU-IRB-2026-0248
  title           text not null,
  pi              text not null,
  email           text not null,
  college         text not null,
  review_type     text not null,                   -- Exempt / Expedited / Full Board
  design          text,
  funding         text,
  participants    integer default 0,
  start_date      date,
  abstract        text,
  vulnerable      boolean default false,
  bio_spec        boolean default false,
  identifiable    boolean default false,
  coi             boolean default false,
  doc_filenames   jsonb default '[]'::jsonb,
  status          text not null default 'Pending',
  submitted_at    timestamptz not null default now()
);
create index if not exists erb_protocols_submitted_idx
  on erb_protocols(submitted_at desc);
create index if not exists erb_protocols_status_idx
  on erb_protocols(status);
create index if not exists erb_protocols_college_idx
  on erb_protocols(college);

-- ============================================================
-- 2. Grant Projects (proposals)
-- ============================================================
create table if not exists grant_projects (
  id                   bigserial primary key,
  project_id           text unique not null,       -- MCU-IHG-2026-0039
  title                text not null,
  pi                   text not null,
  email                text not null,
  college              text not null,
  track                text not null,              -- Basic / Applied / Translational / ...
  duration             integer not null,           -- months
  budget               numeric(12,2) not null,
  team                 text,
  outputs              text,
  abstract             text,
  aligned_with_agenda  boolean default false,
  doc_filenames        jsonb default '[]'::jsonb,
  status               text not null default 'Submitted',
  submitted_at         timestamptz not null default now()
);
create index if not exists grant_projects_submitted_idx
  on grant_projects(submitted_at desc);
create index if not exists grant_projects_status_idx
  on grant_projects(status);

-- ============================================================
-- 3. Grant Reports
-- ============================================================
create table if not exists grant_reports (
  id              bigserial primary key,
  grant_id        text not null,                   -- references an existing grant
  pi              text not null,
  report_type     text not null,                   -- Quarterly / Mid-term / Annual / Final
  completion      integer default 0,
  period_from     date,
  period_to       date,
  accomplishments text not null,
  deliverables    text,
  outputs         text,
  challenges      text,
  doc_filenames   jsonb default '[]'::jsonb,
  status          text not null default 'Under Review',
  submitted_at    timestamptz not null default now()
);
create index if not exists grant_reports_submitted_idx
  on grant_reports(submitted_at desc);
create index if not exists grant_reports_grant_idx
  on grant_reports(grant_id);

-- ============================================================
-- 4. Budget Entries
-- ============================================================
create table if not exists budget_entries (
  id                  bigserial primary key,
  grant_id            text not null,
  date                date not null,
  category            text not null,
  amount              numeric(12,2) not null,
  voucher             text,
  payee               text,
  description         text not null,
  receipt_filenames   jsonb default '[]'::jsonb,
  submitted_at        timestamptz not null default now()
);
create index if not exists budget_entries_grant_idx
  on budget_entries(grant_id);
create index if not exists budget_entries_date_idx
  on budget_entries(date desc);

-- ============================================================
-- 5. Row-Level Security (RLS)
-- ============================================================
-- DEFAULT POSTURE: open for prototype.
-- Switch to restrictive policies once you wire authentication.
--
-- To enable RLS later:
--   alter table erb_protocols enable row level security;
--   create policy "allow public insert" on erb_protocols
--     for insert with check (true);
--   create policy "allow public select" on erb_protocols
--     for select using (true);
--   (repeat for each table)
--
-- For production with auth, restrict insert to authenticated MCU emails:
--   create policy "mcu_email_only" on erb_protocols
--     for insert with check (auth.email() like '%@mcu.edu.ph');

-- ============================================================
-- 6. Helpful views (optional — for the analytics page)
-- ============================================================
create or replace view v_erb_summary as
  select status, count(*) as n
  from erb_protocols
  group by status;

create or replace view v_grants_by_college as
  select college, count(*) as n_projects, sum(budget) as total_budget
  from grant_projects
  group by college
  order by total_budget desc;

create or replace view v_budget_by_category as
  select category, count(*) as n_entries, sum(amount) as total_spent
  from budget_entries
  group by category
  order by total_spent desc;

-- ============================================================
-- DONE. Tables ready for the Streamlit dashboard.
-- ============================================================
