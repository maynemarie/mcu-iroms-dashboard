-- ============================================================
-- IRO Presentations & Reports library — run once in Supabase SQL Editor
-- ============================================================

create table if not exists iro_documents (
  id              bigserial primary key,
  title           text not null,
  doc_type        text not null,                  -- Presentation / Annual Report / Quarterly / etc.
  doc_date        date,                           -- when presented / reported
  presenter       text,                           -- author / speaker / department
  description     text,
  tags            text,                           -- comma-separated keywords
  filename        text not null,
  storage_path    text not null,
  uploaded_by     text not null,
  uploaded_at     timestamptz not null default now(),
  download_count  integer default 0
);

create index if not exists iro_docs_type_idx  on iro_documents(doc_type);
create index if not exists iro_docs_date_idx  on iro_documents(doc_date desc);
create index if not exists iro_docs_when_idx  on iro_documents(uploaded_at desc);

alter table iro_documents disable row level security;
