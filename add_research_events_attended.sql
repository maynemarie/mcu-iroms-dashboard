-- ============================================================
-- Research Events Attended — parent + child schema.
-- Run once in Supabase SQL Editor.
--   • One event row in research_events_attended
--   • Many attendee rows in research_event_attendees (cascade on delete)
-- ============================================================

create table if not exists research_events_attended (
  id                  bigserial primary key,
  event_title         text not null,
  event_type          text,                  -- Conference / Congress / Workshop / Seminar / Webinar / Symposium / Other
  start_date          date not null,
  end_date            date,                  -- nullable, for multi-day
  location            text,                  -- city, country, or "Online"
  organizer           text,                  -- host organisation
  certificate         text,                  -- filename or link (event-level)
  notes               text,
  submitted_by        text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz,
  updated_by          text
);

create index if not exists rea_start_idx on research_events_attended(start_date desc);
create index if not exists rea_type_idx  on research_events_attended(event_type);

alter table research_events_attended disable row level security;

-- Migration: drop columns from earlier per-event-single-attendee design.
alter table research_events_attended drop column if exists attendee_name;
alter table research_events_attended drop column if exists attendees_list;
alter table research_events_attended drop column if exists num_attendees;
alter table research_events_attended drop column if exists attendee_college;
alter table research_events_attended drop column if exists role;
alter table research_events_attended drop column if exists presentation_title;
alter table research_events_attended drop column if exists funding_source;
alter table research_events_attended drop column if exists cost;

-- Child table: one row per MCU attendee at the event.
create table if not exists research_event_attendees (
  id                  bigserial primary key,
  event_id            bigint not null references research_events_attended(id) on delete cascade,
  attendee_name       text not null,
  attendee_college    text,
  role                text,                  -- Attendee / Presenter / Keynote Speaker / Panelist / Chair / Moderator
  presentation_title  text,                  -- only if presenting
  award               text,                  -- e.g., "Best Paper", "1st Place", "Honorable Mention"
  created_at          timestamptz not null default now()
);

-- Migration for existing installs:
alter table research_event_attendees add column if not exists award text;

create index if not exists rea_att_event_idx on research_event_attendees(event_id);
create index if not exists rea_att_name_idx  on research_event_attendees(attendee_name);
create index if not exists rea_att_role_idx  on research_event_attendees(role);

alter table research_event_attendees disable row level security;
