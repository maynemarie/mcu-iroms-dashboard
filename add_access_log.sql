-- ============================================================
-- access_log — record each successful dashboard login
-- Run once in the Supabase SQL Editor.
-- ============================================================
-- One row is written every time a user successfully signs in
-- (who, their role, and when). The admin-only "User Management"
-- page reads this to show recent sign-ins.
-- ============================================================

create table if not exists access_log (
  id            bigserial primary key,
  email         text not null,
  full_name     text,
  role          text,
  logged_in_at  timestamptz not null default now()
);

create index if not exists access_log_when_idx
  on access_log(logged_in_at desc);

-- Row-Level Security. The dashboard talks to Supabase with the anon
-- key (it manages its own cookie session), so reads/writes must be
-- permitted for that key — the same posture as the other dashboard
-- tables. Viewing is additionally gated to admins in the app itself
-- (the User Management page calls require_admin()).
alter table access_log enable row level security;

drop policy if exists access_log_all on access_log;
create policy access_log_all
  on access_log
  for all
  using (true)
  with check (true);
