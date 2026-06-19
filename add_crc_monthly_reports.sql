-- College Research Coordinator (CRC) monthly report submissions.
-- One row per (college, reporting_year, reporting_month).
-- Run once in the Supabase SQL Editor.

create table if not exists public.crc_monthly_reports (
    id                    uuid primary key default gen_random_uuid(),
    reporting_year        integer       not null check (reporting_year between 2024 and 2035),
    reporting_month       integer       not null check (reporting_month between 1 and 12),
    college               text          not null,
    crc_name              text          not null,
    crc_email             text          not null,
    new_grants_count      integer       not null default 0 check (new_grants_count >= 0),
    publications_count    integer       not null default 0 check (publications_count >= 0),
    workshops_count       integer       not null default 0 check (workshops_count >= 0),
    trainings_count       integer       not null default 0 check (trainings_count >= 0),
    activities_summary    text          not null,
    accomplishments       text,
    challenges            text,
    next_month_plans      text,
    doc_filenames         jsonb         default '[]'::jsonb,
    status                text          not null default 'Submitted'
                                       check (status in ('Submitted', 'Under Review',
                                                         'Accepted', 'Returned')),
    submitted_at          timestamptz   not null default now()
);

create index if not exists crc_monthly_reports_period_idx
    on public.crc_monthly_reports (reporting_year desc, reporting_month desc);

create index if not exists crc_monthly_reports_college_idx
    on public.crc_monthly_reports (college);
