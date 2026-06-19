-- ============================================================
-- Allow public inserts/selects for the prototype.
-- Run this once in Supabase SQL Editor.
--
-- ⚠️ For production, replace these with authenticated policies.
-- ============================================================

-- Disable RLS entirely for prototype simplicity
alter table scopus_publications disable row level security;
alter table scopus_audit_log    disable row level security;
alter table erb_protocols       disable row level security;
alter table grant_projects      disable row level security;
alter table grant_reports       disable row level security;
alter table budget_entries      disable row level security;
