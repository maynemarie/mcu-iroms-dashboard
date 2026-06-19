-- ============================================================
-- Capacity-Building Workshops table — run once in Supabase SQL Editor
-- ============================================================

create table if not exists capacity_workshops (
  id              bigserial primary key,
  title           text not null,
  start_date      date not null,
  end_date        date,                           -- NULL if same-day
  speakers        text not null,                  -- comma-separated list
  workshop_type   text,                           -- Methods / Publication / Ethics / IP / etc.
  target_audience text,                           -- Faculty / Students / Both
  attendees       integer,
  materials       text,                           -- filename or link
  feedback_score  numeric(3, 2),                  -- e.g., 4.65 / 5
  status          text not null default 'Upcoming',  -- Upcoming / Completed / Cancelled
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz,
  updated_by      text
);

create index if not exists workshops_date_idx on capacity_workshops(start_date desc);
create index if not exists workshops_type_idx on capacity_workshops(workshop_type);
create index if not exists workshops_status_idx on capacity_workshops(status);

alter table capacity_workshops disable row level security;
