-- ============================================================
-- External Grants — research grants received from funders
-- outside MCU (DOST, CHED, PCHRD, industry, international, etc.).
-- Run once in Supabase SQL Editor.
-- ============================================================

create table if not exists external_grants (
  id              bigserial primary key,
  title           text not null,
  pi              text,                              -- principal investigator
  college         text,
  funding_source  text not null,                     -- DOST-PCHRD / CHED / Industry / International / Other
  funder_name     text,                              -- specific funder name (e.g., "Pfizer Inc.")
  amount          numeric,                           -- PHP value
  currency        text default 'PHP',
  duration_months integer,
  date_submitted  date,                              -- proposal submission date
  date_awarded    date,                              -- award notice date
  start_date      date,                              -- project start
  end_date        date,                              -- project end
  status          text default 'Submitted',          -- Submitted / In Review / Awarded / Active / Completed / Cancelled
  contract_ref    text,                              -- contract / award number
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz,
  updated_by      text,
  submitted_by    text
);

create index if not exists ext_grants_source_idx
  on external_grants(funding_source);
create index if not exists ext_grants_status_idx
  on external_grants(status);
create index if not exists ext_grants_start_idx
  on external_grants(start_date desc);

alter table external_grants disable row level security;

-- Migration for existing installs:
alter table external_grants add column if not exists date_submitted date;
alter table external_grants add column if not exists date_awarded   date;
