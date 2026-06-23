-- ============================================================
-- Allow the 'crc' role in allowed_users
-- ============================================================
-- Run this ONLY IF adding/modifying a user with the new "crc" role
-- fails with a check-constraint error (e.g. violates check constraint
-- "allowed_users_role_check"). If assigning crc already works, you do
-- not need this.
--
-- It drops any existing CHECK constraint on allowed_users.role and
-- recreates one that permits all three roles. Idempotent and safe to
-- re-run. Run in the Supabase SQL Editor.
-- ============================================================

do $$
declare c text;
begin
  for c in
    select conname
    from pg_constraint
    where conrelid = 'public.allowed_users'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%role%'
  loop
    execute format('alter table public.allowed_users drop constraint %I', c);
  end loop;
end $$;

alter table public.allowed_users
  add constraint allowed_users_role_check
  check (role in ('admin', 'standard', 'crc'));
