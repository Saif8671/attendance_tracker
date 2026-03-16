-- ============================================================
-- AttendX — Complete Supabase Schema (idempotent)
-- Organized from user_table.xlsx data model
-- Covers: profiles, faculty, classes, students, subjects + attendance
--
-- Paste into: Supabase Dashboard → SQL Editor → Run
-- ============================================================

-- ============================================================
-- EXTENSIONS
-- ============================================================
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";


-- ============================================================
-- 1. PROFILES
-- Extends Supabase auth.users — covers student / faculty / admin
-- ============================================================
create table if not exists public.profiles (
  id           uuid        primary key references auth.users(id) on delete cascade,
  role         text        not null check (role in ('student', 'faculty', 'admin')),
  full_name    text        not null,
  username     text        unique not null,
  phone        text,
  email        text        unique,
  avatar_url   text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
comment on table public.profiles is 'One row per auth user (student / faculty / admin)';

-- Auto-create a profile row whenever someone signs up
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into public.profiles (id, role, full_name, username, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'role',      'student'),
    coalesce(new.raw_user_meta_data->>'full_name', 'New User'),
    coalesce(new.raw_user_meta_data->>'username',  split_part(new.email, '@', 1)),
    new.email
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Keep updated_at current
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.set_updated_at();


-- ============================================================
-- 2. DEPARTMENTS
-- ============================================================
create table if not exists public.departments (
  id         uuid primary key default uuid_generate_v4(),
  name       text not null,
  code       text not null unique,
  created_at timestamptz not null default now()
);
comment on table public.departments is 'Academic departments / branches';

insert into public.departments (name, code) values
  ('Computer Science & Engineering',  'CSE'),
  ('Computer Science & AI/ML',        'CSM'),
  ('Electronics & Communication Eng', 'ECE'),
  ('Mechanical Engineering',          'MECH')
on conflict (code) do nothing;


-- ============================================================
-- 3. SUBJECTS
-- ============================================================
create table if not exists public.subjects (
  id            uuid primary key default uuid_generate_v4(),
  department_id uuid not null references public.departments(id) on delete cascade,
  name          text not null,
  code          text not null unique,
  semester      int  not null check (semester between 1 and 8),
  credits       int  not null default 3,
  created_at    timestamptz not null default now()
);
comment on table public.subjects is 'Academic subjects linked to departments';

create index if not exists idx_subjects_department on public.subjects(department_id);
create index if not exists idx_subjects_semester   on public.subjects(semester);

insert into public.subjects (department_id, name, code, semester) values
  ((select id from public.departments where code = 'CSE'), 'Mathematics', 'MA401', 4),
  ((select id from public.departments where code = 'CSE'), 'Science',     'SC301', 3),
  ((select id from public.departments where code = 'CSE'), 'Physics',     'PH201', 2),
  ((select id from public.departments where code = 'CSM'), 'Algorithms',  'CS601', 6),
  ((select id from public.departments where code = 'CSM'), 'Python',      'CS401', 4),
  ((select id from public.departments where code = 'CSM'), 'AI & ML',     'CS501', 5)
on conflict (code) do nothing;


-- ============================================================
-- 4. CLASSES
-- Each class = a section of a department for one academic year/semester
-- ============================================================
create table if not exists public.classes (
  id                  uuid primary key default uuid_generate_v4(),
  department_id       uuid not null references public.departments(id) on delete cascade,
  section             text not null default 'A',
  semester            int  not null check (semester between 1 and 8),
  academic_year_start date not null,
  academic_year_end   date not null,
  room                text,
  max_students        int  default 60,
  created_at          timestamptz not null default now(),
  unique (department_id, section, semester, academic_year_start)
);
comment on table public.classes is 'A class = department section for a semester/year';

create index if not exists idx_classes_department on public.classes(department_id);
create index if not exists idx_classes_semester   on public.classes(semester);

insert into public.classes (department_id, section, semester, academic_year_start, academic_year_end) values
  ((select id from public.departments where code = 'CSE'),  'A', 4, '2025-07-01', '2026-05-31'),
  ((select id from public.departments where code = 'CSM'),  'A', 4, '2025-07-01', '2026-05-31'),
  ((select id from public.departments where code = 'ECE'),  'A', 4, '2025-07-01', '2026-05-31'),
  ((select id from public.departments where code = 'MECH'), 'A', 4, '2025-07-01', '2026-05-31')
on conflict (department_id, section, semester, academic_year_start) do nothing;


-- ============================================================
-- 5. STUDENT PROFILES
-- Extends profiles table for student-specific fields
-- ============================================================
create table if not exists public.student_profiles (
  id         uuid primary key references public.profiles(id) on delete cascade,
  roll_no    text unique not null,
  class_id   uuid not null references public.classes(id) on delete restrict,
  dob        date,
  address    text,
  guardian   text,
  created_at timestamptz not null default now()
);
comment on table public.student_profiles is 'Student-specific data linked to profiles and class';

create index if not exists idx_student_profiles_class on public.student_profiles(class_id);


-- ============================================================
-- 6. FACULTY PROFILES
-- ============================================================
create table if not exists public.faculty_profiles (
  id            uuid primary key references public.profiles(id) on delete cascade,
  employee_id   text unique,
  department_id uuid references public.departments(id) on delete set null,
  designation   text default 'Assistant Professor',
  joined_date   date,
  created_at    timestamptz not null default now()
);
comment on table public.faculty_profiles is 'Faculty-specific data: department, designation, employee ID';

create index if not exists idx_faculty_profiles_dept on public.faculty_profiles(department_id);


-- ============================================================
-- 7. FACULTY ASSIGNMENTS
-- Maps faculty → class → subject
-- ============================================================
create table if not exists public.faculty_assignments (
  id         uuid primary key default uuid_generate_v4(),
  faculty_id uuid not null references public.faculty_profiles(id) on delete cascade,
  class_id   uuid not null references public.classes(id)          on delete cascade,
  subject_id uuid not null references public.subjects(id)         on delete cascade,
  created_at timestamptz not null default now(),
  unique (faculty_id, class_id, subject_id)
);
comment on table public.faculty_assignments is 'Maps faculty → class → subject';

create index if not exists idx_assignments_faculty  on public.faculty_assignments(faculty_id);
create index if not exists idx_assignments_class    on public.faculty_assignments(class_id);
create index if not exists idx_assignments_subject  on public.faculty_assignments(subject_id);


-- ============================================================
-- 8. SESSIONS
-- A single lecture/lab on a specific date
-- ============================================================
create table if not exists public.sessions (
  id            uuid primary key default uuid_generate_v4(),
  assignment_id uuid not null references public.faculty_assignments(id) on delete cascade,
  session_date  date not null,
  start_time    time not null,
  end_time      time not null,
  topic         text,
  session_type  text not null default 'lecture'
                      check (session_type in ('lecture','lab','tutorial','exam')),
  status        text not null default 'scheduled'
                      check (status in ('scheduled','ongoing','completed','cancelled')),
  notes         text,
  created_at    timestamptz not null default now()
);
comment on table public.sessions is 'Individual class meetings linked to a faculty assignment';

create index if not exists idx_sessions_assignment on public.sessions(assignment_id);
create index if not exists idx_sessions_date       on public.sessions(session_date);
create index if not exists idx_sessions_status     on public.sessions(status);


-- ============================================================
-- 9. QR TOKENS
-- ============================================================
create table if not exists public.qr_tokens (
  id         uuid primary key default uuid_generate_v4(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  token      text not null unique default encode(gen_random_bytes(16), 'hex'),
  expires_at timestamptz not null,
  is_active  boolean not null default true,
  created_at timestamptz not null default now()
);
comment on table public.qr_tokens is 'Short-lived tokens generated per session for QR check-in';

create index if not exists idx_qr_tokens_session on public.qr_tokens(session_id);
create index if not exists idx_qr_tokens_token   on public.qr_tokens(token);
create index if not exists idx_qr_tokens_active  on public.qr_tokens(is_active, expires_at);

-- Helper: generate a fresh QR token (deactivates old ones)
create or replace function public.generate_qr_token(
  p_session_id       uuid,
  p_validity_minutes int default 15
)
returns public.qr_tokens
language plpgsql
security definer
as $$
declare v public.qr_tokens;
begin
  update public.qr_tokens set is_active = false where session_id = p_session_id;
  insert into public.qr_tokens (session_id, expires_at)
  values (p_session_id, now() + (p_validity_minutes || ' minutes')::interval)
  returning * into v;
  return v;
end;
$$;


-- ============================================================
-- 10. ATTENDANCE RECORDS
-- One row per student per session
-- ============================================================
create table if not exists public.attendance_records (
  id          uuid primary key default uuid_generate_v4(),
  session_id  uuid not null references public.sessions(id)         on delete cascade,
  student_id  uuid not null references public.student_profiles(id) on delete cascade,
  qr_token_id uuid          references public.qr_tokens(id)        on delete set null,
  status      text not null default 'present'
              check (status in ('present','absent','late','excused')),
  method      text not null default 'qr'
              check (method in ('qr','manual','proxy_blocked')),
  device_info jsonb,
  marked_at   timestamptz not null default now(),
  unique (session_id, student_id)
);
comment on table public.attendance_records is 'Core attendance — one row per student per session';

create index if not exists idx_attendance_session on public.attendance_records(session_id);
create index if not exists idx_attendance_student on public.attendance_records(student_id);
create index if not exists idx_attendance_status  on public.attendance_records(status);


-- ============================================================
-- 11. VIEWS (ready-made queries for dashboards)
-- ============================================================

-- 11a. Full student info (profile + roll + class + department)
create or replace view public.v_students as
select
  p.id,
  p.full_name,
  p.username,
  p.email,
  p.phone,
  sp.roll_no,
  c.section,
  c.semester,
  d.name  as department_name,
  d.code  as department_code
from       public.profiles         p
join       public.student_profiles sp on sp.id = p.id
join       public.classes          c  on c.id  = sp.class_id
join       public.departments      d  on d.id  = c.department_id
where p.role = 'student';

-- 11b. Full faculty info with their teaching assignments
create or replace view public.v_faculty_assignments as
select
  p.id                as faculty_id,
  p.full_name         as faculty_name,
  fp.employee_id,
  fp.designation,
  d.name              as department_name,
  c.section,
  c.semester,
  sub.name            as subject_name,
  sub.code            as subject_code
from       public.profiles            p
join       public.faculty_profiles    fp  on fp.id         = p.id
join       public.faculty_assignments fa  on fa.faculty_id = p.id
join       public.classes             c   on c.id          = fa.class_id
join       public.subjects            sub on sub.id        = fa.subject_id
left join  public.departments         d   on d.id          = fp.department_id
where p.role = 'faculty';

-- 11c. Attendance % per student per subject
create or replace view public.v_attendance_summary as
select
  sp.id                            as student_id,
  p.full_name                      as student_name,
  sp.roll_no,
  sub.name                         as subject_name,
  sub.code                         as subject_code,
  count(distinct s.id)             as total_sessions,
  count(distinct ar.id)
    filter (where ar.status in ('present','late')) as attended,
  round(
    count(distinct ar.id) filter (where ar.status in ('present','late'))::numeric
    / nullif(count(distinct s.id), 0) * 100, 2
  )                                as attendance_pct
from       public.student_profiles    sp
join       public.profiles            p   on p.id   = sp.id
join       public.classes             c   on c.id   = sp.class_id
join       public.faculty_assignments fa  on fa.class_id = c.id
join       public.subjects            sub on sub.id = fa.subject_id
left join  public.sessions            s   on s.assignment_id = fa.id
                                          and s.status = 'completed'
left join  public.attendance_records  ar  on ar.session_id = s.id
                                          and ar.student_id = sp.id
group by sp.id, p.full_name, sp.roll_no, sub.name, sub.code;

-- 11d. At-risk students (below 75%)
create or replace view public.v_at_risk_students as
select * from public.v_attendance_summary where attendance_pct < 75;

-- 11e. Session roll call (who attended a specific session)
create or replace view public.v_session_roll as
select
  s.id                           as session_id,
  s.session_date,
  s.topic,
  sub.name                       as subject_name,
  d.code                         as department,
  c.section,
  p.full_name                    as student_name,
  sp.roll_no,
  coalesce(ar.status, 'absent')  as status,
  ar.method,
  ar.marked_at
from       public.sessions           s
join       public.faculty_assignments fa  on fa.id          = s.assignment_id
join       public.subjects            sub on sub.id         = fa.subject_id
join       public.classes             c   on c.id           = fa.class_id
join       public.departments         d   on d.id           = c.department_id
join       public.student_profiles    sp  on sp.class_id    = c.id
join       public.profiles            p   on p.id           = sp.id
left join  public.attendance_records  ar  on ar.session_id  = s.id
                                          and ar.student_id = sp.id;


-- ============================================================
-- 12. ROW-LEVEL SECURITY (RLS)
-- ============================================================
alter table public.profiles            enable row level security;
alter table public.student_profiles    enable row level security;
alter table public.faculty_profiles    enable row level security;
alter table public.faculty_assignments enable row level security;
alter table public.departments         enable row level security;
alter table public.subjects            enable row level security;
alter table public.classes             enable row level security;
alter table public.sessions            enable row level security;
alter table public.qr_tokens           enable row level security;
alter table public.attendance_records  enable row level security;

-- Drop old policies (idempotent reruns)
drop policy if exists "Read departments"               on public.departments;
drop policy if exists "Read subjects"                  on public.subjects;
drop policy if exists "Read classes"                   on public.classes;
drop policy if exists "Own profile"                    on public.profiles;
drop policy if exists "Own profile update"             on public.profiles;
drop policy if exists "Own student profile"            on public.student_profiles;
drop policy if exists "Own faculty profile"            on public.faculty_profiles;
drop policy if exists "Faculty see own assignments"    on public.faculty_assignments;
drop policy if exists "Students see class assignments" on public.faculty_assignments;
drop policy if exists "Faculty see own sessions"       on public.sessions;
drop policy if exists "Students see class sessions"    on public.sessions;
drop policy if exists "Faculty see own QR tokens"      on public.qr_tokens;
drop policy if exists "Students see active QR tokens"  on public.qr_tokens;
drop policy if exists "Students view own attendance"   on public.attendance_records;
drop policy if exists "Faculty view session attendance" on public.attendance_records;
drop policy if exists "Students mark own QR attendance" on public.attendance_records;
drop policy if exists "Faculty manage attendance"      on public.attendance_records;

-- Everyone authenticated can read departments, subjects, classes
create policy "Read departments" on public.departments for select
  using (auth.role() = 'authenticated');
create policy "Read subjects" on public.subjects for select
  using (auth.role() = 'authenticated');
create policy "Read classes" on public.classes for select
  using (auth.role() = 'authenticated');

-- Users see/update their own profile
create policy "Own profile" on public.profiles for select
  using (auth.uid() = id);
create policy "Own profile update" on public.profiles for update
  using (auth.uid() = id);

-- Students see their own student profile
create policy "Own student profile" on public.student_profiles for select
  using (auth.uid() = id);

-- Faculty see their own faculty profile
create policy "Own faculty profile" on public.faculty_profiles for select
  using (auth.uid() = id);

-- Faculty see their own assignments
create policy "Faculty see own assignments" on public.faculty_assignments for select
  using (faculty_id = auth.uid());

-- Students see assignments for their class
create policy "Students see class assignments" on public.faculty_assignments for select
  using (
    exists (
      select 1
      from public.student_profiles sp
      where sp.id = auth.uid() and sp.class_id = class_id
    )
  );

-- Sessions: faculty see own; students see via class
create policy "Faculty see own sessions" on public.sessions for select
  using (
    exists (
      select 1
      from public.faculty_assignments fa
      where fa.id = assignment_id and fa.faculty_id = auth.uid()
    )
  );

create policy "Students see class sessions" on public.sessions for select
  using (
    exists (
      select 1
      from public.faculty_assignments fa
      join public.student_profiles sp on sp.class_id = fa.class_id
      where fa.id = assignment_id and sp.id = auth.uid()
    )
  );

-- QR tokens: faculty see own session tokens
create policy "Faculty see own QR tokens" on public.qr_tokens for select
  using (
    exists (
      select 1
      from public.sessions s
      join public.faculty_assignments fa on fa.id = s.assignment_id
      where s.id = session_id and fa.faculty_id = auth.uid()
    )
  );

-- Students see only active/unexpired tokens for their class
create policy "Students see active QR tokens" on public.qr_tokens for select
  using (
    is_active = true and expires_at > now()
    and exists (
      select 1
      from public.sessions s
      join public.faculty_assignments fa on fa.id = s.assignment_id
      join public.student_profiles sp    on sp.class_id = fa.class_id
      where s.id = session_id and sp.id = auth.uid()
    )
  );

-- Attendance: students see own; faculty see their sessions
create policy "Students view own attendance" on public.attendance_records for select
  using (student_id = auth.uid());

create policy "Faculty view session attendance" on public.attendance_records for select
  using (
    exists (
      select 1
      from public.sessions s
      join public.faculty_assignments fa on fa.id = s.assignment_id
      where s.id = session_id and fa.faculty_id = auth.uid()
    )
  );

-- Students mark themselves via QR only
create policy "Students mark own QR attendance" on public.attendance_records for insert
  with check (
    student_id = auth.uid()
    and method = 'qr'
    and exists (
      select 1
      from public.qr_tokens qt
      where qt.id = qr_token_id and qt.is_active = true and qt.expires_at > now()
    )
  );

-- Faculty can manage attendance for their sessions
create policy "Faculty manage attendance" on public.attendance_records for all
  using (
    exists (
      select 1
      from public.sessions s
      join public.faculty_assignments fa on fa.id = s.assignment_id
      where s.id = session_id and fa.faculty_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.sessions s
      join public.faculty_assignments fa on fa.id = s.assignment_id
      where s.id = session_id and fa.faculty_id = auth.uid()
    )
  );

-- ============================================================
-- DONE ✓
-- ============================================================
