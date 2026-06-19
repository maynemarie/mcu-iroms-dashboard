-- ============================================================
-- MCU Research Journal — issues + articles tables.
-- Run once in Supabase SQL Editor.
-- ============================================================

-- 1. Issue-level metadata (one row per Vol/No)
create table if not exists mcu_journal_issues (
  id                bigserial primary key,
  volume            text not null,
  issue             text not null,
  publication_year  integer not null,
  publication_month integer,                       -- e.g., 6 = June, 12 = December
  editor            text,
  co_editor         text,
  theme             text,                          -- optional special-issue theme
  isbn_or_issn      text,                          -- e.g., "ISSN 2012-3884 (print)"
  pdf_filename      text,
  pdf_storage_path  text,
  cover_filename    text,
  cover_storage_path text,
  doi               text,
  status            text not null default 'Published',  -- Draft / Under Review / Published
  notes             text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz,
  updated_by        text,
  unique(volume, issue)
);

create index if not exists journal_issue_year_idx
  on mcu_journal_issues(publication_year desc);
create index if not exists journal_issue_status_idx
  on mcu_journal_issues(status);

-- 2. Article-level metadata (many rows per issue)
create table if not exists mcu_journal_articles (
  id              bigserial primary key,
  issue_id        bigint references mcu_journal_issues(id) on delete cascade,
  title           text not null,
  authors         text,
  college         text,
  page_start      integer,
  page_end        integer,
  abstract        text,
  keywords        text,
  doi             text,
  pdf_path        text,
  created_at      timestamptz not null default now()
);

create index if not exists journal_articles_issue_idx
  on mcu_journal_articles(issue_id);

-- 3. Disable RLS for prototype
alter table mcu_journal_issues   disable row level security;
alter table mcu_journal_articles disable row level security;

-- 4. Seed the Volume 12, No. 1 issue (the one we reviewed)
insert into mcu_journal_issues
  (volume, issue, publication_year, publication_month,
   editor, co_editor, isbn_or_issn, status, notes)
values
  ('12', '1', 2026, 1,
   'Irene A. Padron, LPT, MEd, MBA, DBA',
   'Nieves L. Capili, MSc',
   'ISSN 2012-3884 (print)',
   'Draft',
   'January 2026 draft v.2. Under review by IRO Editorial Committee.')
on conflict (volume, issue) do nothing;
