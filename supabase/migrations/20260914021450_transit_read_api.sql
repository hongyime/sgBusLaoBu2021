-- Public historical transit data is read-only; legacy user records stay in a
-- private Storage bucket and are never included in these lookup tables.
create schema transit;
revoke all on schema transit from public, anon, authenticated;
grant usage on schema transit to anon, authenticated, service_role;

create table transit.stops (
  code integer primary key,
  description text not null,
  latitude double precision not null,
  longitude double precision not null
);
create index stops_latitude_longitude_idx on transit.stops (latitude, longitude);
create table transit.routes (
  service text not null,
  direction integer not null,
  sequence integer not null,
  stop_code text not null,
  primary key (service, direction, sequence)
);
create index routes_stop_code_idx on transit.routes (stop_code);
create table transit.station_stops (
  stop_code integer primary key references transit.stops(code),
  station text not null,
  line text not null
);
create table transit.facts (
  id boolean primary key default true check (id),
  payload jsonb not null
);
create table transit.archive_manifest (
  snapshot text not null,
  source_path text not null,
  bytes bigint not null,
  sha256 text not null check (length(sha256) = 64),
  object_path text not null,
  primary key (snapshot, source_path)
);

alter table transit.stops enable row level security;
alter table transit.routes enable row level security;
alter table transit.station_stops enable row level security;
alter table transit.facts enable row level security;
alter table transit.archive_manifest enable row level security;
revoke all on all tables in schema transit from public, anon, authenticated;
grant select on transit.stops, transit.routes, transit.station_stops, transit.facts to anon, authenticated;
grant all on all tables in schema transit to service_role;
create policy read_public_transit on transit.stops for select to anon, authenticated using (true);
create policy read_public_transit on transit.routes for select to anon, authenticated using (true);
create policy read_public_transit on transit.station_stops for select to anon, authenticated using (true);
create policy read_public_transit on transit.facts for select to anon, authenticated using (true);

create function public.bus_search(p_lat double precision, p_lon double precision, p_radius double precision)
returns jsonb language plpgsql stable security invoker
set search_path = ''
set statement_timeout = '2s'
as $$
declare result jsonb;
begin
  if p_lat is null or p_lon is null or p_radius is null
     or not (p_lat between -90 and 90 and p_lon between -180 and 180 and p_radius between 0.1 and 1.0) then
    raise exception 'Invalid coordinates or radius' using errcode = '22023';
  end if;
  -- Transit stops are in Singapore. The slightly expanded bounding box is a
  -- superset of every supported <=1 km circle, including its boundary.
  with nearby as materialized (
    select s.*, 12742 * asin(sqrt(least(1.0, greatest(0.0,
      power(sin(radians(s.latitude-p_lat)/2),2)
      + cos(radians(p_lat))*cos(radians(s.latitude))*power(sin(radians(s.longitude-p_lon)/2),2)
    )))) as distance
    from transit.stops s
    where s.latitude between p_lat-p_radius/110.0 and p_lat+p_radius/110.0
      and s.longitude between p_lon-p_radius/110.0 and p_lon+p_radius/110.0
  ), limited as materialized (
    select n.code as busstopcode, n.description as board_busstopdescription,
      n.latitude as busstoplat, n.longitude as busstoplon,
      n.distance, board.service as busservice, board.direction,
      board.sequence as board_sequence, dest.sequence as destination_sequence,
      dest.sequence-board.sequence as numberofstops,
      alight.description as alight_busstopdescription,
      station.station as mrt_station, station.line as mrt_line
    from nearby n
    join transit.routes board on board.stop_code=n.code::text
    join transit.routes dest on dest.service=board.service
      and dest.direction=board.direction and dest.sequence>board.sequence
    join transit.station_stops station on station.stop_code::text=dest.stop_code
    join transit.stops alight on alight.code=station.stop_code
    where n.distance<=p_radius
    order by n.distance, n.code, board.service, board.direction, board.sequence, dest.sequence
    limit 201
  ), numbered as (
    select *, row_number() over (order by distance,busstopcode,busservice,direction,board_sequence,destination_sequence) as rn
    from limited
  )
  select jsonb_build_object(
    'results', coalesce(jsonb_agg(to_jsonb(numbered)-'rn' order by rn) filter(where rn<=200),'[]'::jsonb),
    'has_more', count(*)>200
  ) into result from numbered;
  return result;
end;
$$;

create function public.bus_facts()
returns jsonb language sql stable security invoker
set search_path = '' set statement_timeout = '2s'
as $$ select payload from transit.facts where id=true limit 1 $$;
revoke all on function public.bus_search(double precision,double precision,double precision) from public;
revoke all on function public.bus_facts() from public;
grant execute on function public.bus_search(double precision,double precision,double precision) to anon, authenticated, service_role;
grant execute on function public.bus_facts() to anon, authenticated, service_role;

comment on schema transit is 'Immutable historical bus snapshot; import is owner-operated only. No location collection or scheduled refresh.';
-- Supabase's optional DDL event hook is not an application RPC. Event-trigger
-- execution remains available to its owner after removing public API grants.
do $$ begin
  if to_regprocedure('public.rls_auto_enable()') is not null then
    execute 'revoke execute on function public.rls_auto_enable() from public, anon, authenticated';
  end if;
end $$;
notify pgrst, 'reload schema';
