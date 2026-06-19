-- Minutes of IRO Meeting.
-- One row per meeting.

create table if not exists public.iro_meeting_minutes (
    id            uuid primary key default gen_random_uuid(),
    meeting_date  date           not null,
    meeting_time  time,
    meeting_title text,
    chairperson   text,
    attendees     text           not null,
    agenda        text,
    minutes       text,
    action_items  text,
    next_meeting  date,
    doc_filenames jsonb          default '[]'::jsonb,
    doc_path      text,
    submitted_at  timestamptz    not null default now(),
    submitted_by  text,
    updated_at    timestamptz    not null default now(),
    updated_by    text
);

alter table public.iro_meeting_minutes disable row level security;

create index if not exists iro_meeting_minutes_date_idx
    on public.iro_meeting_minutes (meeting_date desc);

-- Migrations for existing installs:
alter table public.iro_meeting_minutes
    add column if not exists meeting_time time;
alter table public.iro_meeting_minutes
    add column if not exists doc_path text;
