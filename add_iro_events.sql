-- ============================================================
-- IRO Calendar of Events — run once in Supabase SQL Editor
-- ============================================================

create table if not exists iro_events (
  id              bigserial primary key,
  title           text not null,
  event_date      date not null,
  end_date        date,                          -- nullable, for multi-day events
  event_type      text not null,                 -- Workshop / Deadline / Meeting / Congress / etc.
  location        text,
  organizer       text,
  description     text,
  link            text,
  all_day         boolean default true,
  start_time      time,
  end_time        time,
  color           text,                          -- optional hex color for the dot
  status          text default 'Scheduled',      -- Scheduled / Cancelled / Postponed
  notes           text,
  created_by      text,
  created_at      timestamptz not null default now()
);

create index if not exists events_date_idx on iro_events(event_date);
create index if not exists events_type_idx on iro_events(event_type);

alter table iro_events disable row level security;
