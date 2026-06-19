-- ============================================================
-- Add audit columns to scopus_publications — run once in Supabase SQL Editor
-- ============================================================

-- Add audit-trail columns to the existing table
alter table scopus_publications
  add column if not exists updated_at timestamptz,
  add column if not exists updated_by text,
  add column if not exists update_note text;

-- Create an audit log table for full edit history (one row per edit)
create table if not exists scopus_audit_log (
  id              bigserial primary key,
  publication_id  bigint not null references scopus_publications(id) on delete cascade,
  changed_by      text not null,
  change_note     text,
  changed_fields  jsonb,                       -- {"quartile": {"old": "Q2", "new": "Q1"}, ...}
  changed_at      timestamptz not null default now()
);

create index if not exists scopus_audit_pub_idx
  on scopus_audit_log(publication_id);
create index if not exists scopus_audit_when_idx
  on scopus_audit_log(changed_at desc);
