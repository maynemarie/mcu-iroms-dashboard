-- Per-transaction breakdown linked to a budget line item in iro_budget_items.
-- Each row is one disbursement (RFAA/RFP), payee, amount, etc.

create table if not exists public.iro_budget_transactions (
    id                uuid primary key default gen_random_uuid(),
    budget_item_id    uuid references public.iro_budget_items(id) on delete cascade,
    fiscal_year       integer        not null,
    budget_ref_no     text           not null,
    activity_name     text           not null,
    transaction_date  date,
    rfaa_no           text,
    rfp_no            text,
    payee             text,
    requested_by      text,
    college           text,
    amount            numeric(14, 2) not null default 0,
    notes             text,
    created_at        timestamptz    not null default now(),
    created_by        text
);

alter table public.iro_budget_transactions disable row level security;

create index if not exists iro_budget_transactions_ref_idx
    on public.iro_budget_transactions (fiscal_year, budget_ref_no);
create index if not exists iro_budget_transactions_date_idx
    on public.iro_budget_transactions (transaction_date desc);
