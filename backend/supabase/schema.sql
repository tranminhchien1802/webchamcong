-- Initial schema for a new Supabase project. Existing tables need explicit
-- ALTER TABLE migrations; CREATE TABLE IF NOT EXISTS does not retrofit them.
create sequence if not exists public.employee_number_seq start with 1;

create or replace function public.generate_employee_id()
returns text
language sql
volatile
as $$
    select 'emp_' || case
        when value < 1000 then lpad(value::text, 3, '0')
        else value::text
    end
    from (select nextval('public.employee_number_seq') as value) generated;
$$;

create table if not exists public.employees (
    employee_id text primary key default public.generate_employee_id(),
    name text not null,
    image_filename text not null,
    face_encoding double precision[] not null,
    created_at timestamptz not null default now(),
    constraint employee_name_not_empty check (length(trim(name)) > 0),
    constraint face_encoding_has_128_values
        check (cardinality(face_encoding) = 128)
);

create unique index if not exists employees_name_unique_ci
    on public.employees (lower(trim(name)));

create table if not exists public.attendance (
    attendance_date date not null,
    employee_id text not null
        references public.employees(employee_id) on delete cascade,
    is_arrive boolean not null default true,
    arrived_at timestamptz not null,
    departed_at timestamptz,
    last_distance double precision not null,
    constraint attendance_employee_day_pk
        primary key (attendance_date, employee_id),
    constraint attendance_departure_after_arrival
        check (departed_at is null or departed_at >= arrived_at)
);

create index if not exists attendance_employee_id_index
    on public.attendance (employee_id);

alter table public.employees enable row level security;
alter table public.attendance enable row level security;

revoke all on table public.employees from anon, authenticated;
revoke all on table public.attendance from anon, authenticated;
grant all on table public.employees to service_role;
grant all on table public.attendance to service_role;
grant usage, select on sequence public.employee_number_seq to service_role;
grant execute on function public.generate_employee_id() to service_role;
