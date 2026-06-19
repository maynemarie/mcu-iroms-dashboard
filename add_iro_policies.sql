-- ============================================================
-- IRO Policies — institutional research policies library.
-- Run once in Supabase SQL Editor.
-- ============================================================

create table if not exists iro_policies (
  id                 bigserial primary key,
  policy_title       text not null,
  policy_type        text not null,                -- e.g., "Research Ethics", "Authorship", "Data Management"
  updated_by_person  text not null,                -- who updated/owns it
  date_updated       date not null,
  file_filename      text,
  file_storage_path  text,
  notes              text,
  created_at         timestamptz not null default now(),
  uploaded_by        text
);

create index if not exists iro_policies_type_idx on iro_policies(policy_type);
create index if not exists iro_policies_date_idx on iro_policies(date_updated desc);

alter table iro_policies disable row level security;
