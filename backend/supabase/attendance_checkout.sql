-- Run in the Supabase SQL Editor after schema.sql.
alter table public.attendance add column if not exists departed_at timestamptz;
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'attendance_departure_after_arrival' and conrelid = 'public.attendance'::regclass) then
        alter table public.attendance add constraint attendance_departure_after_arrival
            check (departed_at is null or departed_at >= arrived_at);
    end if;
end $$;
