-- ============================================================
-- Faculty-Led Journals — issues + articles tables.
-- Mirrors mcu_journal_issues / mcu_journal_articles, with an
-- extra journal_name + college + faculty_lead so multiple
-- college-level journals can coexist.
-- Run once in Supabase SQL Editor.
-- ============================================================

create table if not exists faculty_led_journal_issues (
  id                 bigserial primary key,
  journal_name       text not null,                    -- e.g., "Journal of Medical Education"
  college            text,                              -- e.g., College of Medicine
  faculty_lead       text,                              -- lead faculty / editor-in-chief
  volume             text not null,
  issue              text not null,
  publication_year   integer not null,
  publication_month  integer,
  editor             text,
  co_editor          text,
  theme              text,
  isbn_or_issn       text,
  pdf_filename       text,
  pdf_storage_path   text,
  cover_filename     text,
  cover_storage_path text,
  doi                text,
  status             text not null default 'Draft',     -- Draft / Under Review / Published
  notes              text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz,
  updated_by         text,
  unique(journal_name, volume, issue)
);

create index if not exists fl_journal_year_idx
  on faculty_led_journal_issues(publication_year desc);
create index if not exists fl_journal_name_idx
  on faculty_led_journal_issues(journal_name);
create index if not exists fl_journal_status_idx
  on faculty_led_journal_issues(status);

create table if not exists faculty_led_journal_articles (
  id          bigserial primary key,
  issue_id    bigint references faculty_led_journal_issues(id) on delete cascade,
  title       text not null,
  authors     text,
  college     text,
  page_start  integer,
  page_end    integer,
  abstract    text,
  keywords    text,
  doi         text,
  pdf_path    text,
  created_at  timestamptz not null default now()
);

create index if not exists fl_journal_articles_issue_idx
  on faculty_led_journal_articles(issue_id);

alter table faculty_led_journal_issues   disable row level security;
alter table faculty_led_journal_articles disable row level security;
