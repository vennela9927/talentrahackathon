"""Step 23 - Data Generation at Scale.

Seeded, reproducible generator for the Step 13 profiles. It writes
  master/  organisations (accounts, organisations, one recruiter each) for the Step 24 master seed
  b001/    the initial source delivery in the four legacy contracts, with planted defects
  b002/    a delta: corrections, exact re-sends, key reuse, late in-order and late out-of-order events
  b003/    stale re-sends of records that b002 corrected
  expected_quarantine.csv  every planted defect with the reason the pipeline must give it
  manifest.json            seed, parameters, row counts and SHA256 of every file

Valid records follow the Step 13 distributions; planted defects are extra rows, so the valid
population matches the profile exactly. Nothing here is real personal data (Step 12):
names are synthetic, e-mail domains are example.invalid.

Usage: step23_generate.py --profile bench|dev|demo [--seed 23] [--out DIR] [--no-defects]
"""
import argparse
import csv
import datetime as dt
import gzip
import time
from pathlib import Path

import numpy as np

from common import DATA, PROFILES, SOURCE_SYSTEM, open_csv_gz, sha256_file, write_json
from step24_reference import CITIES, FAMILIES, ROLES, INDUSTRIES, LANGUAGES, NAMES

NULL = "\\N"
UTC = dt.timezone.utc
WINDOW_START = dt.datetime(2025, 11, 1, tzinfo=UTC)   # first application day
WINDOW_DAYS = 304                                      # through 2026-08-31; every path completes by 2026-10-31
SNAPSHOT = dt.datetime(2026, 10, 31, 23, 59, 59, tzinfo=UTC)

# Tuned so the bench profile meets the Step 13 targets (see step23_profile_check.py)
ORG_SIGMA, JOB_SIGMA, ORG_TRAFFIC_ALPHA = 0.93, 0.92, 0.60
CANDIDATE_SIGMA = 0.8
MAX_APPS_PER_JOB = 2500
PEAK_DAY_FACTOR = 2.5
NULL_RATE = 0.10
# Large deliveries arrive in parts: applications and the status events of those same applications
PART_APPLICATIONS = 1_000_000

# Application paths (status codes are the native job_application vocabulary).
# Reach: 100% applied -> 28% shortlisted -> 14% interviewed -> 5% offered -> 3% joined (Step 13 R-27..28).
PATHS = [
    (("applied",), 0.28),
    (("applied", "rejected"), 0.40),
    (("applied", "withdrawn"), 0.04),
    (("applied", "shortlisted"), 0.02),
    (("applied", "shortlisted", "rejected"), 0.10),
    (("applied", "shortlisted", "withdrawn"), 0.02),
    (("applied", "shortlisted", "interviewed"), 0.01),
    (("applied", "shortlisted", "interviewed", "rejected"), 0.07),
    (("applied", "shortlisted", "interviewed", "withdrawn"), 0.01),
    (("applied", "shortlisted", "interviewed", "offered"), 0.002),
    (("applied", "shortlisted", "interviewed", "offered", "rejected"), 0.003),
    (("applied", "shortlisted", "interviewed", "offered", "withdrawn"), 0.015),
    (("applied", "shortlisted", "interviewed", "offered", "joined"), 0.03),
]
CANDIDATE_ACTIONS = {"withdrawn"}          # every other transition is made by the recruiter
GAP_DAYS = {"shortlisted": (1, 7), "interviewed": (3, 10), "offered": (2, 10), "joined": (7, 25),
            "rejected": (1, 10), "withdrawn": (1, 10)}
WEEKDAY = [1.25, 1.2, 1.05, 1.0, 0.95, 0.6, 0.45]     # Mon..Sun, recruiter/candidate working-week shape
SEASON = {1: 1.3, 2: 1.3, 3: 1.3, 8: 1.1, 9: 1.1}       # appraisal season, campus season
CHANNELS = [("portal", 0.55), ("mobile_app", 0.25), ("referral", 0.08), ("campus", 0.07), ("consultant", 0.05)]

CANDIDATE_HEADER = ["event_id", "correlation_id", "schema_version", "occurred_at", "source_version", "external_key",
                    "email", "person_name", "preferred_language", "city_id", "headline", "birth_date",
                    "profile_status", "content_language"]
JOB_HEADER = ["event_id", "correlation_id", "schema_version", "occurred_at", "source_version", "external_key",
              "organisation_id", "job_role_id", "employment_type_reference_value_id", "work_type_reference_value_id",
              "city_id", "title", "description", "positions", "status_reference_value_id",
              "publish_state_reference_value_id", "open_to_consultant", "salary_min", "salary_max", "currency_code",
              "salary_disclosure_reference_value_id", "source_timezone", "content_language"]
APPLICATION_HEADER = ["event_id", "correlation_id", "schema_version", "occurred_at", "source_version", "external_key",
                      "candidate_key", "job_key", "organisation_key", "applied_at", "source_channel"]
EVENT_HEADER = ["event_id", "correlation_id", "schema_version", "occurred_at", "source_version", "external_key",
                "application_key", "organisation_key", "from_status", "to_status", "actor_type", "actor_key"]
ORG_HEADER = ["organisation_key", "account_name", "organisation_name", "industry_code", "status_code",
              "recruiter_email", "recruiter_name", "created_at"]

# Native reference ids used by the legacy.job_requirement.v1 contract (shared vocabulary, BR-031)
EMPLOYMENT = {"gig": 81, "general_staffing": 82, "professional_staffing": 83, "permanent": 84,
              "apprentice": 85, "campus": 86, "consultant": 87, "managed_remote": 88}
WORK = {"onsite": 99, "hybrid": 100, "remote": 101}
JOB_STATUS = {"closed": 95, "draft": 96, "paused": 97, "published": 98}
PUBLISH = {"draft": 89, "published": 90, "unpublished": 91}
DISCLOSURE = {"unknown": 92, "not_applicable": 93, "disclosed": 94}


def iso(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_iso(seconds):
    return iso(dt.datetime.fromtimestamp(int(seconds), UTC))


class Writer:
    """One gzip CSV per contract per batch, tracking line numbers for expected-defect references."""

    def __init__(self, path, header):
        self.path = path
        self.handle, self.w = open_csv_gz(path, header)
        self.lines = 1

    def row(self, values):
        self.w.writerow([NULL if v is None else v for v in values])
        self.lines += 1
        return self.lines

    def raw(self, text):
        self.handle.write(text + "\n")
        self.lines += 1
        return self.lines

    def close(self):
        self.handle.close()


class Generator:
    def __init__(self, profile, seed, out, defects):
        self.p = PROFILES[profile]
        self.profile = profile
        self.seed = seed
        self.out = Path(out)
        self.defects = defects
        self.rng = np.random.default_rng(seed)
        self.expected = []          # (batch, file, contract, external_key, line, reason, field_path)
        self.event_seq = 0
        self.timings = {}

    # ------------------------------------------------------------------ helpers
    def eid(self, batch):
        self.event_seq += 1
        return f"{SOURCE_SYSTEM}-{batch}-{self.event_seq:09d}"

    def expect(self, batch, file, contract, key, line, reason, field):
        self.expected.append((batch, file, contract, key, line, reason, field))

    def pick(self, choices, size):
        labels = [c for c, _ in choices]
        probs = np.array([w for _, w in choices], dtype=float)
        return np.array(labels, dtype=object)[self.rng.choice(len(labels), size=size, p=probs / probs.sum())]

    # ------------------------------------------------------------------ structure
    def build(self):
        p, rng = self.p, self.rng
        n_o, n_c, n_j, n_a = p["organisations"], p["candidates"], p["jobs"], p["applications"]

        # Organisations: lognormal size; 40% of organisations post ~78% of jobs (Step 13 R-18..20)
        self.org_w = rng.lognormal(0, ORG_SIGMA, n_o)
        jobs_per_org = rng.multinomial(n_j, self.org_w / self.org_w.sum())
        self.job_org = rng.permutation(np.repeat(np.arange(n_o), jobs_per_org))

        # Applications per job: heavy right tail, bigger organisations attract more traffic
        job_w = rng.lognormal(0, JOB_SIGMA, n_j) * self.org_w[self.job_org] ** ORG_TRAFFIC_ALPHA
        apj = rng.multinomial(n_a, job_w / job_w.sum())
        excess = int(np.maximum(apj - MAX_APPS_PER_JOB, 0).sum())
        apj = np.minimum(apj, MAX_APPS_PER_JOB)
        while excess:                               # re-home the capped excess so the total stays exact
            room = MAX_APPS_PER_JOB - apj
            extra = rng.multinomial(excess, (job_w * (room > 0)) / (job_w * (room > 0)).sum())
            extra = np.minimum(extra, room)
            apj += extra
            excess -= int(extra.sum())
        self.apps_per_job = apj
        app_job = np.repeat(np.arange(n_j), apj)

        # Candidates per application: activity skew, (candidate, job) unique (job_application uniqueness)
        cand_cdf = np.cumsum(rng.lognormal(0, CANDIDATE_SIGMA, n_c))
        cand_cdf /= cand_cdf[-1]
        app_cand = np.searchsorted(cand_cdf, rng.random(n_a))
        for _ in range(50):
            pair = app_job.astype(np.int64) * n_c + app_cand
            _, first = np.unique(pair, return_index=True)
            dup = np.ones(n_a, bool)
            dup[first] = False
            if not dup.any():
                break
            app_cand[dup] = np.searchsorted(cand_cdf, rng.random(int(dup.sum())))
        else:
            raise RuntimeError("could not resolve duplicate candidate/job pairs")
        order = rng.permutation(n_a)
        self.app_job, self.app_cand = app_job[order], app_cand[order]

        # Application days: weekday, season and a few peak days at 2.5x the median day (Step 13 peak traffic)
        days = [WINDOW_START + dt.timedelta(days=d) for d in range(WINDOW_DAYS)]
        w = np.array([WEEKDAY[d.weekday()] * SEASON.get(d.month, 1.0) for d in days])
        peaks = rng.choice(np.where(np.array([d.month in (8, 9, 1) for d in days]))[0], 4, replace=False)
        w[peaks] = PEAK_DAY_FACTOR * np.median(w)
        self.peak_days = sorted(days[i].date().isoformat() for i in peaks)
        day = rng.choice(WINDOW_DAYS, size=n_a, p=w / w.sum())
        # IST working-hour peaks 10:00-13:00 and 19:00-22:00 (Step 13 seasonality sheet), stored as UTC
        hour_w = np.array([1, 1, 1, 1, 1, 1, 2, 4, 6, 8, 12, 12, 12, 9, 8, 7, 6, 6, 7, 11, 11, 11, 6, 2], float)
        hour_ist = rng.choice(24, size=n_a, p=hour_w / hour_w.sum())
        base = WINDOW_START.timestamp()
        self.app_ts = base + day * 86400 + hour_ist * 3600 - 19800 + rng.integers(0, 3600, n_a)

        # Jobs are created before their first application (applied_at >= job created_at)
        first_app = np.full(n_j, np.inf)
        np.minimum.at(first_app, self.app_job, self.app_ts)
        no_apps = np.isinf(first_app)
        first_app[no_apps] = base + rng.integers(0, WINDOW_DAYS * 86400, int(no_apps.sum()))
        self.job_ts = first_app - rng.integers(3600, 21 * 86400, n_j)

        # Candidates registered before their first application
        cand_first = np.full(n_c, np.inf)
        np.minimum.at(cand_first, self.app_cand, self.app_ts)
        idle = np.isinf(cand_first)
        cand_first[idle] = base + rng.integers(0, WINDOW_DAYS * 86400, int(idle.sum()))
        self.cand_ts = cand_first - rng.integers(3600, 60 * 86400, n_c)

        # Status paths per application
        probs = np.array([w for _, w in PATHS])
        self.app_path = rng.choice(len(PATHS), size=n_a, p=probs / probs.sum())

    # ------------------------------------------------------------------ master data
    def write_master(self):
        rng, n_o = self.rng, self.p["organisations"]
        Path(self.out / "master").mkdir(parents=True, exist_ok=True)
        statuses = self.pick([("verified", 0.92), ("pending", 0.06), ("suspended", 0.02)], n_o)
        industries = rng.choice(len(INDUSTRIES), n_o)
        f = Writer(self.out / "master" / "organisations.csv.gz", ORG_HEADER)
        for i in range(n_o):
            k = i + 1
            f.row([k, f"Synthetic Account {k:06d}", f"Synthetic Employer {k:06d}", INDUSTRIES[industries[i]][0],
                   statuses[i], f"recruiter{k:06d}@org{k:06d}.example.invalid", f"Recruiter {k:06d} Synthetic",
                   iso(WINDOW_START - dt.timedelta(days=int(rng.integers(30, 720))))])
        f.close()
        self.org_status = statuses

    # ------------------------------------------------------------------ b001
    def candidate_row(self, batch, key, i, version=1, headline_override=None):
        rng = self.rng
        lang = self.cand_lang[i]
        first, last = NAMES[lang]
        name = f"{first[int(rng.integers(len(first)))]} {last[int(rng.integers(len(last)))]}"
        city = NULL if self.cand_null_city[i] else self.cand_city[i]
        headline = headline_override or (NULL if self.cand_null_head[i] else self.cand_headline[i])
        birth = NULL if self.cand_null_birth[i] else self.cand_birth[i]
        return [self.eid(batch), f"corr-{key}", 1, epoch_iso(self.cand_ts[i]), version, key,
                f"c{i + 1:07d}@candidates.example.invalid", name, lang, city, headline, birth,
                self.cand_status[i], lang]

    def prepare_candidates(self):
        rng, n_c = self.rng, self.p["candidates"]
        self.cand_lang = self.pick(LANGUAGES, n_c)
        city_ids = np.array([c[0] for c in CITIES])
        city_w = np.array([c[5] for c in CITIES], float)
        self.cand_city = city_ids[rng.choice(len(CITIES), n_c, p=city_w / city_w.sum())]
        self.cand_null_city = rng.random(n_c) < NULL_RATE
        self.cand_null_head = rng.random(n_c) < NULL_RATE
        self.cand_null_birth = rng.random(n_c) < NULL_RATE
        fam = rng.choice(len(FAMILIES), n_c, p=[f[2] for f in FAMILIES])
        years = rng.integers(0, 16, n_c)
        self.cand_headline = np.array([f"{FAMILIES[f][1]} professional, {y} yrs" for f, y in zip(fam, years)],
                                      dtype=object)
        ages = rng.integers(18, 58, n_c)
        self.cand_birth = np.array([f"{2026 - a}-{int(m):02d}-{int(d):02d}" for a, m, d in
                                    zip(ages, rng.integers(1, 13, n_c), rng.integers(1, 29, n_c))], dtype=object)
        self.cand_status = self.pick([("active", 0.9), ("hidden", 0.07), ("draft", 0.03)], n_c)

    def job_row(self, batch, key, j, version=1, title_suffix=""):
        rng = self.rng
        fam = self.job_family[j]
        role = self.job_role[j]
        salary = None if self.job_null_salary[j] else self.job_salary[j]
        return [self.eid(batch), f"corr-{key}", 1, epoch_iso(self.job_ts[j]), version, key,
                int(self.job_org[j]) + 1, role[0], self.job_employment[j], self.job_work[j],
                NULL if self.job_null_city[j] else self.job_city[j],
                f"{role[2]}{title_suffix}", f"Synthetic {FAMILIES[fam][1]} requirement for {role[2]}.",
                self.job_positions[j] + (1 if title_suffix else 0), JOB_STATUS["published"], PUBLISH["published"],
                "true" if self.job_consultant[j] else "false",
                None if salary is None else f"{salary[0]}.00", None if salary is None else f"{salary[1]}.00",
                None if salary is None else "INR",
                DISCLOSURE["unknown"] if salary is None else DISCLOSURE["disclosed"], "Asia/Kolkata",
                "en"]

    def prepare_jobs(self):
        rng, n_j = self.rng, self.p["jobs"]
        fam = rng.choice(len(FAMILIES), n_j, p=[f[2] for f in FAMILIES])
        self.job_family = fam
        roles_by_family = {i: [r for r in ROLES if r[1] == FAMILIES[i][0]] for i in range(len(FAMILIES))}
        self.job_role = [roles_by_family[f][int(rng.integers(len(roles_by_family[f])))] for f in fam]
        # Top 8 Tier-1 cities hold 68% of postings (Step 13 R-21..22)
        city_ids = np.array([c[0] for c in CITIES])
        tier1 = np.array([c[4] for c in CITIES])
        cw = np.where(tier1, 0.68 / tier1.sum(), 0.32 / (~tier1).sum())
        self.job_city = city_ids[rng.choice(len(CITIES), n_j, p=cw)]
        self.job_null_city = rng.random(n_j) < NULL_RATE
        self.job_null_salary = rng.random(n_j) < NULL_RATE
        blue = np.isin(fam, [i for i, f in enumerate(FAMILIES) if f[0].startswith("BLUE")])
        it = np.isin(fam, [i for i, f in enumerate(FAMILIES) if f[0].startswith("IT")])
        lo = np.where(blue, rng.integers(12, 25, n_j), np.where(it, rng.integers(35, 120, n_j),
                                                                 rng.integers(20, 60, n_j))) * 10_000
        self.job_salary = list(zip(lo, lo + rng.integers(1, 8, n_j) * 50_000))
        self.job_positions = np.where(blue, rng.integers(5, 60, n_j), rng.integers(1, 6, n_j))
        emp_it = self.pick([("permanent", 0.7), ("professional_staffing", 0.15), ("consultant", 0.1),
                            ("campus", 0.05)], n_j)
        emp_blue = self.pick([("general_staffing", 0.55), ("permanent", 0.35), ("apprentice", 0.1)], n_j)
        emp_other = self.pick([("permanent", 0.75), ("general_staffing", 0.15), ("campus", 0.1)], n_j)
        self.job_employment = [EMPLOYMENT[e] for e in np.where(it, emp_it, np.where(blue, emp_blue, emp_other))]
        work_it = self.pick([("hybrid", 0.5), ("onsite", 0.35), ("remote", 0.15)], n_j)
        self.job_work = [WORK[w] if i else WORK["onsite"] for w, i in zip(work_it, it)]
        self.job_consultant = rng.random(n_j) < 0.2

    def write_b001(self):
        rng = self.rng
        n_c, n_j, n_a = self.p["candidates"], self.p["jobs"], self.p["applications"]
        d = self.out / "b001"
        d.mkdir(parents=True, exist_ok=True)

        # Defects are extra rows interleaved at random positions; ones that depend on an earlier valid
        # row (e-mail and candidate/job pair conflicts) go last so the valid row is always seen first.
        t = time.time()
        f = Writer(d / "candidates.csv.gz", CANDIDATE_HEADER)
        bad = self.candidate_defects(n_c) if self.defects else []
        slots = dict(zip(rng.choice(n_c, len([b for b in bad if not b[2]]), replace=False),
                         [b for b in bad if not b[2]]))
        for i in range(n_c):
            f.row(self.candidate_row("b001", f"CAN-{i + 1:07d}", i))
            if i in slots:
                self.emit_defect(f, "b001", "legacy.candidate_account.v1", slots[i])
        for b in [b for b in bad if b[2]]:
            self.emit_defect(f, "b001", "legacy.candidate_account.v1", b)
        f.close()
        self.timings["candidates"] = round(time.time() - t, 1)

        t = time.time()
        f = Writer(d / "jobs.csv.gz", JOB_HEADER)
        bad = self.job_defects(n_j) if self.defects else []
        slots = dict(zip(rng.choice(n_j, len(bad), replace=False), bad))
        for j in range(n_j):
            f.row(self.job_row("b001", f"JOB-{j + 1:07d}", j))
            if j in slots:
                self.emit_defect(f, "b001", "legacy.job_requirement.v1", slots[j])
        f.close()
        self.timings["jobs"] = round(time.time() - t, 1)

        # Applications and their status events. Some final events are held back for b002 (late, in order).
        t = time.time()
        fa = fe = None
        bad_apps = self.application_defects(n_a) if self.defects else []
        app_slots = dict(zip(rng.choice(n_a, len([b for b in bad_apps if not b[2]]), replace=False),
                             [b for b in bad_apps if not b[2]]))
        channels = self.pick(CHANNELS, n_a)
        gaps = {s: rng.integers(lo * 86400, hi * 86400, n_a) for s, (lo, hi) in GAP_DAYS.items()}
        ends_rejected = np.array([p[-1] == "rejected" and len(p) > 1 for p, _ in PATHS])
        terminal_rejected = ends_rejected[self.app_path]
        late_n = min(2000, int(terminal_rejected.sum() // 10)) if self.defects else 0
        self.late_apps = set(rng.choice(np.where(terminal_rejected)[0], late_n, replace=False).tolist())
        self.held_events = []
        # Last delivered event per application in b001 (time, status, ordinal), for the defect and delta writers
        self.last_ts = np.zeros(n_a)
        self.last_status = np.empty(n_a, dtype=object)
        self.last_n = np.zeros(n_a, dtype=np.int8)
        for a in range(n_a):
            if a % PART_APPLICATIONS == 0:
                for w in (fa, fe):
                    if w:
                        w.close()
                part = a // PART_APPLICATIONS + 1
                fa = Writer(d / f"applications.p{part:02d}.csv.gz", APPLICATION_HEADER)
                fe = Writer(d / f"status_events.p{part:02d}.csv.gz", EVENT_HEADER)
            key = f"APP-{a + 1:08d}"
            j, c = int(self.app_job[a]), int(self.app_cand[a])
            org_key = int(self.job_org[j]) + 1
            fa.row([self.eid("b001"), f"corr-{key}", 1, epoch_iso(self.app_ts[a]), 1, key,
                    f"CAN-{c + 1:07d}", f"JOB-{j + 1:07d}", org_key, epoch_iso(self.app_ts[a]), channels[a]])
            if a in app_slots:
                self.emit_defect(fa, "b001", "legacy.job_application.v1", app_slots[a])
            ts, prev = self.app_ts[a], None
            path = PATHS[self.app_path[a]][0]
            for n, status in enumerate(path):
                if n:
                    ts = ts + gaps[status][a]
                actor = ("candidate", f"CAN-{c + 1:07d}") if (n == 0 or status in CANDIDATE_ACTIONS) \
                    else ("recruiter", f"ORG-{org_key:06d}")
                ev = [None, f"corr-{key}", 1, epoch_iso(ts), 1, f"{key}-E{n + 1}", key, org_key, prev, status,
                      actor[0], actor[1]]
                if a in self.late_apps and n == len(path) - 1:
                    self.held_events.append(ev)
                else:
                    ev[0] = self.eid("b001")
                    fe.row(ev)
                    self.last_ts[a], self.last_status[a], self.last_n[a] = ts, status, n + 1
                prev = status
        # Defects that refer to earlier rows go in the last part, after every row they refer to
        for b in [b for b in bad_apps if b[2]]:
            self.emit_defect(fa, "b001", "legacy.job_application.v1", b)
        # Event defects extend chains written above, so they are chosen once every chain is known
        for b in self.event_defects(n_a) if self.defects else []:
            self.emit_defect(fe, "b001", "legacy.application_status_event.v1", b)
        fa.close()
        fe.close()
        self.timings["applications_and_events"] = round(time.time() - t, 1)

    def emit_defect(self, writer, batch, contract, defect):
        key, reason, _, field, row = defect
        line = writer.raw(row) if isinstance(row, str) else writer.row(row)
        self.expect(batch, writer.path.name, contract, key, line, reason, field)

    # ------------------------------------------------------------------ planted defects
    def candidate_defects(self, n_c):
        """(external_key, reason, place_last, field_path, row) for each planted candidate defect."""
        out, k = [], 0
        rng = self.rng

        def base(i):
            nonlocal k
            k += 1
            key = f"CAN-X{k:06d}"
            row = self.candidate_row("b001", key, i)
            row[6] = f"x{k:06d}@candidates.example.invalid"
            return key, row
        scale = max(1, n_c // 10_000)
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[6] = None
            out.append((key, "MISSING_REQUIRED", False, "email", row))
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[6] = row[6].replace("@", "-at-")
            out.append((key, "INVALID_FORMAT", False, "email", row))
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[11] = "1990-02-30"
            out.append((key, "INVALID_FORMAT", False, "birth_date", row))
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[11] = "2019-06-01"
            out.append((key, "OUT_OF_RANGE", False, "birth_date", row))
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[9] = 999_999
            out.append((key, "UNKNOWN_REFERENCE", False, "city_id", row))
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[12] = "erased"
            out.append((key, "INVALID_STATE", False, "profile_status", row))
        for _ in range(10 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[8] = "fr"
            out.append((key, "UNKNOWN_REFERENCE", False, "preferred_language", row))
        for _ in range(5 * scale):
            key, row = base(int(rng.integers(n_c)))
            row[2] = 2
            out.append((key, "UNSUPPORTED_VERSION", False, "schema_version", row))
        for _ in range(5 * scale):
            key, row = base(int(rng.integers(n_c)))
            line = ",".join("" if v is None else str(v) for v in row[:9])     # truncated record
            out.append((key, "MALFORMED_ROW", False, "$", line))
        for _ in range(10 * scale):                                           # e-mail already owned by another key
            i = int(rng.integers(n_c))
            key, row = base(i)
            row[6] = f"c{i + 1:07d}@candidates.example.invalid"
            out.append((key, "UNIQUE_CONFLICT", True, "email", row))
        return out

    def job_defects(self, n_j):
        out, k, rng = [], 0, self.rng
        scale = max(1, n_j // 1_000)

        def base():
            nonlocal k
            k += 1
            key = f"JOB-X{k:06d}"
            return key, self.job_row("b001", key, int(rng.integers(n_j)))
        for _ in range(2 * scale):
            key, row = base()
            row[6] = self.p["organisations"] + 777
            out.append((key, "UNKNOWN_PARENT", False, "organisation_id", row))
        for _ in range(2 * scale):
            key, row = base()
            row[14] = 65                                   # a job_application status id: wrong vocabulary
            out.append((key, "WRONG_DOMAIN", False, "status_reference_value_id", row))
        for _ in range(2 * scale):
            key, row = base()
            row[13] = 0
            out.append((key, "OUT_OF_RANGE", False, "positions", row))
        for _ in range(2 * scale):
            key, row = base()
            row[17], row[18], row[19], row[20] = "900000.00", "300000.00", "INR", DISCLOSURE["disclosed"]
            out.append((key, "OUT_OF_RANGE", False, "salary_min", row))
        for _ in range(2 * scale):
            key, row = base()
            row[17], row[18], row[19], row[20] = "300000.00", "500000.00", None, DISCLOSURE["disclosed"]
            out.append((key, "INCONSISTENT", False, "currency_code", row))
        for _ in range(2 * scale):
            key, row = base()
            row[11] = None
            out.append((key, "MISSING_REQUIRED", False, "title", row))
        for _ in range(1 * scale):
            key, row = base()
            row[7] = 999_999
            out.append((key, "UNKNOWN_REFERENCE", False, "job_role_id", row))
        return out

    def application_defects(self, n_a):
        out, k, rng = [], 0, self.rng
        n_j, n_c = self.p["jobs"], self.p["candidates"]
        scale = max(1, n_a // 10_000)

        def base(a=None):
            nonlocal k
            k += 1
            a = int(rng.integers(n_a)) if a is None else a
            j, c = int(self.app_job[a]), int(rng.integers(n_c))
            key = f"APP-X{k:07d}"
            return key, [self.eid("b001"), f"corr-{key}", 1, epoch_iso(self.app_ts[a]), 1, key,
                         f"CAN-{c + 1:07d}", f"JOB-{j + 1:07d}", int(self.job_org[j]) + 1,
                         epoch_iso(self.app_ts[a]), "portal"]
        for _ in range(4 * scale):
            key, row = base()
            row[7] = f"JOB-{n_j + 50_000:07d}"
            out.append((key, "UNKNOWN_PARENT", False, "job_key", row))
        for _ in range(4 * scale):
            key, row = base()
            row[6] = f"CAN-{n_c + 50_000:07d}"
            out.append((key, "UNKNOWN_PARENT", False, "candidate_key", row))
        for _ in range(4 * scale):
            key, row = base()
            row[8] = (row[8] % self.p["organisations"]) + 1                  # another tenant's organisation
            out.append((key, "CROSS_ACCOUNT", False, "organisation_key", row))
        for _ in range(4 * scale):
            key, row = base()
            row[9] = "2026-13-45T25:00:00Z"
            out.append((key, "INVALID_FORMAT", False, "applied_at", row))
        for _ in range(2 * scale):
            key, row = base()
            row[9] = "2027-06-01T00:00:00Z"
            out.append((key, "OUT_OF_RANGE", False, "applied_at", row))
        for _ in range(2 * scale):                         # same candidate and job as an existing application
            a = int(rng.integers(n_a))
            key, row = base(a)
            row[6] = f"CAN-{int(self.app_cand[a]) + 1:07d}"
            out.append((key, "UNIQUE_CONFLICT", True, "candidate_key,job_key", row))
        return out

    def event_defects(self, n_a):
        """Planted events extend a valid application's chain, so nothing valid is stranded behind them."""
        out, k, rng = [], 0, self.rng
        scale = max(1, n_a // 10_000)
        used = set()

        def pick(pred):
            while True:
                a = int(rng.integers(n_a))
                if a in used or a in self.late_apps or not self.last_n[a]:
                    continue
                if pred(self.last_status[a]):
                    used.add(a)
                    return a

        def ev(a, frm, to, actor, reason, field, ts=None, app_key=None):
            nonlocal k
            k += 1
            key = f"APP-{a + 1:08d}-X{k}"
            j, c = int(self.app_job[a]), int(self.app_cand[a])
            org = int(self.job_org[j]) + 1
            when = self.last_ts[a] + 86400 if ts is None else ts
            who = f"CAN-{c + 1:07d}" if actor == "candidate" else f"ORG-{org:06d}"
            out.append((key, reason, True, field,
                        [self.eid("b001"), f"corr-APP-{a + 1:08d}", 1, epoch_iso(when), 1, key,
                         app_key or f"APP-{a + 1:08d}", org, frm, to, actor, who]))
        for _ in range(3 * scale):
            a = pick(lambda s: s == "applied")
            ev(a, "applied", "joined", "recruiter", "ILLEGAL_TRANSITION", "from_status,to_status")
        for _ in range(3 * scale):
            a = pick(lambda s: s == "applied")
            ev(a, "applied", "hired", "recruiter", "UNKNOWN_REFERENCE", "to_status")
        for _ in range(3 * scale):
            a = pick(lambda s: s == "applied")
            ev(a, "interviewed", "offered", "recruiter", "CHAIN_BREAK", "from_status")
        for _ in range(3 * scale):
            a = pick(lambda s: s == "applied")
            ev(a, "applied", "shortlisted", "candidate", "ACTOR_NOT_PERMITTED", "actor_type")
        for _ in range(3 * scale):
            a = pick(lambda s: s == "applied")
            ev(a, "applied", "shortlisted", "recruiter", "OUT_OF_RANGE", "occurred_at",
               ts=self.app_ts[a] - 30 * 86400)
        for _ in range(3 * scale):
            a = pick(lambda s: s == "applied")
            ev(a, "applied", "shortlisted", "recruiter", "UNKNOWN_PARENT", "application_key",
               app_key=f"APP-{n_a + 9_000_000 + k:08d}")
        return out

    # ------------------------------------------------------------------ deltas
    def write_b002_b003(self):
        """Delta deliveries: corrections, re-sends, key reuse, late events, then stale versions."""
        rng = self.rng
        n_c, n_j, n_a = self.p["candidates"], self.p["jobs"], self.p["applications"]
        d2, d3 = self.out / "b002", self.out / "b003"
        d2.mkdir(parents=True, exist_ok=True)
        d3.mkdir(parents=True, exist_ok=True)
        scale = max(1, n_c // 10_000)

        # Candidates: exact re-sends (duplicates) and same key + version with different content (key reuse).
        # The b002 candidate file itself is written by copy_resends() from the b001 lines.
        resend = rng.choice(n_c, 10 * scale, replace=False)
        self.resend_candidates = sorted(int(i) for i in resend)
        reuse = rng.choice(np.setdiff1d(np.arange(n_c), resend), 2 * scale, replace=False)
        self.reuse_candidates = sorted(int(i) for i in reuse)

        # Jobs: corrections (version 2) now, stale version 1 re-sends of the same keys in b003
        corr = rng.choice(n_j, max(5, n_j // 200), replace=False)
        f = Writer(d2 / "jobs.csv.gz", JOB_HEADER)
        for j in corr:
            f.row(self.job_row("b002", f"JOB-{j + 1:07d}", int(j), version=2, title_suffix=" (revised)"))
        f.close()
        stale = corr[: max(2, len(corr) // 10)]
        f = Writer(d3 / "jobs.csv.gz", JOB_HEADER)
        for j in stale:
            key = f"JOB-{j + 1:07d}"
            f.row(self.job_row("b003", key, int(j), version=1, title_suffix=" (old copy)"))
            self.expect("b003", f.path.name, "legacy.job_requirement.v1", key, f.lines, "STALE_VERSION",
                        "source_version")
        f.close()
        self.corrected_jobs = sorted(int(j) + 1 for j in corr)

        # Status events: held-back final events arrive late but in order; a few arrive out of order
        f = Writer(d2 / "status_events.csv.gz", EVENT_HEADER)
        for ev in self.held_events:
            ev[0] = self.eid("b002")
            f.row(ev)
        ooo = [a for a in rng.choice(n_a, 400, replace=False).tolist()
               if self.last_n[a] and a not in self.late_apps
               and self.last_status[a] in ("rejected", "withdrawn", "joined")][: max(1, n_a // 50_000)]
        for a in ooo:
            ts, n = self.last_ts[a], int(self.last_n[a])
            key = f"APP-{a + 1:08d}-L{n + 1}"
            org = int(self.job_org[int(self.app_job[a])]) + 1
            f.row([self.eid("b002"), f"corr-APP-{a + 1:08d}", 1, epoch_iso(ts - 3600), 1, key,
                   f"APP-{a + 1:08d}", org, "applied", "withdrawn", "candidate",
                   f"CAN-{int(self.app_cand[a]) + 1:07d}"])
            self.expect("b002", f.path.name, "legacy.application_status_event.v1", key, f.lines,
                        "LATE_OUT_OF_ORDER", "occurred_at")
        f.close()
        self.late_in_order = len(self.held_events)
        self.late_out_of_order = len(ooo)

    def copy_resends(self):
        """Exact re-sends copy b001 lines byte-for-byte; key reuse changes only the headline."""
        want = {f"CAN-{i + 1:07d}": "dup" for i in self.resend_candidates}
        want.update({f"CAN-{i + 1:07d}": "reuse" for i in self.reuse_candidates})
        out = Writer(self.out / "b002" / "candidates.csv.gz", CANDIDATE_HEADER)
        with gzip.open(self.out / "b001" / "candidates.csv.gz", "rt", encoding="utf-8", newline="") as h:
            r = csv.reader(h)
            next(r)
            for row in r:
                kind = want.get(row[5] if len(row) > 5 else None)
                if kind == "dup":
                    out.row([v if v != NULL else None for v in row])
                elif kind == "reuse":
                    row = [v if v != NULL else None for v in row]
                    row[0] = self.eid("b002")
                    row[10] = "Changed headline under the same version"
                    out.row(row)
                    self.expect("b002", out.path.name, "legacy.candidate_account.v1", row[5], out.lines,
                                "KEY_REUSE", "source_version")
        out.close()

    # ------------------------------------------------------------------ run
    def run(self):
        t0 = time.time()
        self.build()
        self.timings["structure"] = round(time.time() - t0, 1)
        self.write_master()
        self.prepare_candidates()
        self.prepare_jobs()
        self.write_b001()
        if self.defects:
            self.write_b002_b003()
            self.copy_resends()
        with open(self.out / "expected_quarantine.csv", "w", encoding="utf-8", newline="") as h:
            w = csv.writer(h, lineterminator="\n")
            w.writerow(["batch", "file", "contract", "external_key", "line", "reason", "field_path"])
            w.writerows(self.expected)
        files = sorted(p for p in self.out.rglob("*") if p.is_file() and p.name != "manifest.json")
        manifest = {
            "step": 23, "profile": self.profile, "seed": self.seed, "generated_at": dt.datetime.now(UTC).isoformat(),
            "targets": self.p, "parameters": {
                "org_sigma": ORG_SIGMA, "job_sigma": JOB_SIGMA, "org_traffic_alpha": ORG_TRAFFIC_ALPHA,
                "candidate_sigma": CANDIDATE_SIGMA, "max_apps_per_job": MAX_APPS_PER_JOB,
                "peak_day_factor": PEAK_DAY_FACTOR, "null_rate": NULL_RATE, "window_start": iso(WINDOW_START),
                "window_days": WINDOW_DAYS, "peak_days": self.peak_days,
                "paths": [[list(p), w] for p, w in PATHS]},
            "deltas": {} if not self.defects else {
                "duplicate_candidate_resends": len(self.resend_candidates),
                "key_reuse_candidates": len(self.reuse_candidates),
                "corrected_jobs": len(self.corrected_jobs),
                "late_in_order_events": self.late_in_order,
                "late_out_of_order_events": self.late_out_of_order},
            "planted_defects": len(self.expected),
            "timings_seconds": self.timings,
            "files": [{"path": p.relative_to(self.out).as_posix(), "bytes": p.stat().st_size,
                       "sha256": sha256_file(p)} for p in files],
        }
        write_json(self.out / "manifest.json", manifest)
        return manifest


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--profile", choices=["bench", "dev", "demo"], required=True)
    a.add_argument("--seed", type=int, default=23)
    a.add_argument("--out", type=Path)
    a.add_argument("--no-defects", action="store_true", help="clean data only (seed sets for dev/demo)")
    args = a.parse_args()
    out = args.out or DATA / f"{args.profile}_seed{args.seed}"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; choose a new --out")
    out.mkdir(parents=True, exist_ok=True)
    m = Generator(args.profile, args.seed, out, not args.no_defects).run()
    print(f"profile={m['profile']} seed={m['seed']} files={len(m['files'])} planted={m['planted_defects']}")
    print("timings", m["timings_seconds"])


if __name__ == "__main__":
    main()
