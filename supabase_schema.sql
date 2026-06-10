-- Run this in the Supabase SQL Editor (https://app.supabase.com → SQL Editor)
-- Creates the subscriptions table with Row Level Security:
--   - Anyone can insert (subscribe)
--   - Anyone can update active=false where token matches (unsubscribe)
--   - Only service role can SELECT (used by notify.py)

create table if not exists subscriptions (
  id                 uuid default gen_random_uuid() primary key,
  type               text not null check (type in ('waterbody','proximity')),
  waterbody_name     text,
  lat                double precision,
  lon                double precision,
  radius_miles       numeric default 10,
  email              text,
  phone              text,
  unsubscribe_token  text unique not null,
  notify_levels      text[] default array['Danger','Warning','Caution','Watch','Mat','Other'],
  last_notified_adv  text,
  created_at         timestamptz default now(),
  active             boolean default true,
  constraint must_have_contact check (email is not null or phone is not null)
);

-- Enable Row Level Security
alter table subscriptions enable row level security;

-- Allow anyone to subscribe (insert)
create policy "allow_insert" on subscriptions
  for insert with check (true);

-- Allow unsubscribe via token (update active=false only)
create policy "allow_unsubscribe" on subscriptions
  for update using (unsubscribe_token = current_setting('app.token', true))
  with check (active = false);

-- Service role (notify.py) bypasses RLS automatically
-- No SELECT policy needed for anon — keeps subscriber data private
