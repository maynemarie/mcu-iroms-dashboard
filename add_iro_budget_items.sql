-- IRO annual operating-budget line items.
-- Sourced from: IRO Budget 2025-2026(RptAPBudgetStatus (1)).csv

-- 1. Create table (fresh installs).
create table if not exists public.iro_budget_items (
    id                       uuid primary key default gen_random_uuid(),
    fiscal_year              integer        not null,
    budget_ref_no            text           not null,
    rfaa_no                  text,
    rfp_no                   text,
    transaction_date         date,
    activity_name            text           not null,
    college                  text           not null default 'Institutional Research Office',
    payee                    text,
    total_budget_allocation  numeric(14, 2) not null default 0,
    explan_budget            numeric(14, 2) not null default 0,
    adjusted_budget          numeric(14, 2) not null default 0,
    utilized_budget          numeric(14, 2) not null default 0,
    outstanding_pending      numeric(14, 2) not null default 0,
    notes                    text,
    submitted_at             timestamptz    not null default now(),
    updated_at               timestamptz    not null default now(),
    updated_by               text,
    unique (fiscal_year, budget_ref_no)
);

create index if not exists iro_budget_items_year_idx
    on public.iro_budget_items (fiscal_year desc);

-- 2. Migrate an existing schema (rename department -> college, add payee).
do $$
begin
    if exists (select 1 from information_schema.columns
               where table_schema = 'public'
                 and table_name = 'iro_budget_items'
                 and column_name = 'department')
       and not exists (select 1 from information_schema.columns
               where table_schema = 'public'
                 and table_name = 'iro_budget_items'
                 and column_name = 'college') then
        alter table public.iro_budget_items
            rename column department to college;
    end if;
end $$;

alter table public.iro_budget_items
    add column if not exists college text not null default 'Institutional Research Office';
alter table public.iro_budget_items
    add column if not exists payee text;
alter table public.iro_budget_items
    add column if not exists rfaa_no text;
alter table public.iro_budget_items
    add column if not exists rfp_no text;
alter table public.iro_budget_items
    add column if not exists transaction_date date;

-- 3. Upsert the FY2025 line items.
insert into public.iro_budget_items
    (fiscal_year, budget_ref_no, activity_name,
     total_budget_allocation, explan_budget, adjusted_budget,
     utilized_budget, outstanding_pending)
values
    (2025, '2025000048', 'Faculty Publication PatentsPresentation (Fees Registration)', 3000000.0, 0.0, 0.0, 235576.27, 0.0),
    (2025, '2025000049', 'Faculty Awards Incentives (Publication Presentation Patents Product)', 1500000.0, 0.0, 0.0, 360000.0, 0.0),
    (2025, '2025000050', 'Inhouse Research Grants for Institution', 2000000.0, 0.0, 0.0, 77500.0, 0.0),
    (2025, '2025000051', 'MCU Research Journal Publication 2 IssuesYear (Printing Honorarium for Paper reviewers', 200000.0, 0.0, 0.0, 37440.0, 0.0),
    (2025, '2025000052', 'Membership Accreditation Research Collaboration -Industry University Government (Fees Transportation Registration)', 300000.0, 0.0, 0.0, 5000.0, 0.0),
    (2025, '2025000053', 'Monthly Coordination Meeting', 60000.0, 0.0, 0.0, 20000.0, 0.0),
    (2025, '2025000054', 'Research Capacity Building', 400000.0, 0.0, 0.0, 207300.0, 0.0),
    (2025, '2025000055', 'Research Colloqium (Institutional and All program)', 500000.0, 0.0, 0.0, 296800.0, 0.0),
    (2025, '2025000056', 'Research Presentation', 1000000.0, 0.0, 0.0, 14611.0, 0.0),
    (2025, '2025000057', 'Student Journal', 150000.0, 0.0, 0.0, 0.0, 0.0),
    (2025, '2025000058', 'Token Representation', 60000.0, 0.0, 0.0, 20600.0, 0.0)
on conflict (fiscal_year, budget_ref_no) do update set
    activity_name           = excluded.activity_name,
    total_budget_allocation = excluded.total_budget_allocation,
    explan_budget           = excluded.explan_budget,
    adjusted_budget         = excluded.adjusted_budget,
    utilized_budget         = excluded.utilized_budget,
    outstanding_pending     = excluded.outstanding_pending,
    updated_at              = now();

-- 4. Seed AY2026-2027 — same 11 line items totalling ₱9,170,000.00, zero
--    utilisation. Ref numbers shift to the 2026-prefix series.
insert into public.iro_budget_items
    (fiscal_year, budget_ref_no, activity_name,
     total_budget_allocation, utilized_budget)
values
    (2026, '2026000048', 'Faculty Publication PatentsPresentation (Fees Registration)', 3000000.0, 0.0),
    (2026, '2026000049', 'Faculty Awards Incentives (Publication Presentation Patents Product)', 1500000.0, 0.0),
    (2026, '2026000050', 'Inhouse Research Grants for Institution', 2000000.0, 0.0),
    (2026, '2026000051', 'MCU Research Journal Publication 2 IssuesYear (Printing Honorarium for Paper reviewers', 200000.0, 0.0),
    (2026, '2026000052', 'Membership Accreditation Research Collaboration -Industry University Government (Fees Transportation Registration)', 300000.0, 0.0),
    (2026, '2026000053', 'Monthly Coordination Meeting', 60000.0, 0.0),
    (2026, '2026000054', 'Research Capacity Building', 400000.0, 0.0),
    (2026, '2026000055', 'Research Colloqium (Institutional and All program)', 500000.0, 0.0),
    (2026, '2026000056', 'Research Presentation', 1000000.0, 0.0),
    (2026, '2026000057', 'Student Journal', 150000.0, 0.0),
    (2026, '2026000058', 'Token Representation', 60000.0, 0.0)
on conflict (fiscal_year, budget_ref_no) do nothing;
