-- ============================================================
-- Extend crc_monthly_reports to track the IRO's strategic goals:
--   (1) fostering research collaborations, and
--   (2) increasing Scopus output from faculty AND students
--       (including the manuscript pipeline that leads to output).
-- Run once in the Supabase SQL Editor. Safe / idempotent.
-- ============================================================

alter table public.crc_monthly_reports
  add column if not exists grants_applied            integer not null default 0
        check (grants_applied >= 0),
  add column if not exists grant_details             text,
  add column if not exists new_collaborations       integer not null default 0
        check (new_collaborations >= 0),
  add column if not exists collaboration_details     text,
  add column if not exists scopus_faculty            integer not null default 0
        check (scopus_faculty >= 0),
  add column if not exists scopus_student            integer not null default 0
        check (scopus_student >= 0),
  add column if not exists students_engaged          integer not null default 0
        check (students_engaged >= 0),
  add column if not exists manuscripts_submitted     integer not null default 0
        check (manuscripts_submitted >= 0),
  add column if not exists manuscripts_under_review  integer not null default 0
        check (manuscripts_under_review >= 0),
  add column if not exists manuscripts_accepted      integer not null default 0
        check (manuscripts_accepted >= 0),
  add column if not exists doc_path                  text;
