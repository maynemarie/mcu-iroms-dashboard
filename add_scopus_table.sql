-- ============================================================
-- Add Scopus publications table — run once in Supabase SQL Editor
-- ============================================================

create table if not exists scopus_publications (
  id              bigserial primary key,
  title           text not null,
  authors         text not null,                   -- "Surname A.B., Surname C.D., ..."
  lead_author     text not null,
  year            integer not null,
  journal         text not null,
  volume          text,
  issue           text,
  pages           text,
  doi             text,
  scopus_link     text,
  quartile        text not null,                   -- Q1 / Q2 / Q3 / Q4
  publication_type text not null,                  -- Article / Review / Conference / Book Chapter / etc.
  college         text not null,
  open_access     boolean default false,
  citation_count  integer default 0,
  funding_source  text,
  acknowledgment  text,
  submitted_at    timestamptz not null default now()
);

create index if not exists scopus_year_idx on scopus_publications(year desc);
create index if not exists scopus_college_idx on scopus_publications(college);
create index if not exists scopus_quartile_idx on scopus_publications(quartile);

-- Analytics view
create or replace view v_scopus_by_year as
  select year, quartile, count(*) as n
  from scopus_publications
  group by year, quartile
  order by year desc, quartile;

create or replace view v_scopus_by_college as
  select college, count(*) as n_pubs, sum(citation_count) as total_citations
  from scopus_publications
  group by college
  order by n_pubs desc;
