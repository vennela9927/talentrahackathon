"""Profile the released seed files: is the shape skewed like the Step 13 profile, or uniform?"""
import collections
import csv
import gzip
import json
import os
import sys


def topshare(counter, frac):
    vals = sorted(counter.values(), reverse=True)
    k = max(1, int(len(vals) * frac))
    return round(sum(vals[:k]) / max(1, sum(vals)), 4)


def main():
    root = sys.argv[1]
    out = {}
    jobs_per_org = collections.Counter()
    with gzip.open(os.path.join(root, "job.csv.gz"), "rt", encoding="utf-8", newline="") as h:
        for r in csv.DictReader(h):
            jobs_per_org[r["organisation_id"]] += 1
    out["organisations"] = len(jobs_per_org)
    out["org_top20pct_share_of_jobs"] = topshare(jobs_per_org, 0.2)
    per_job = collections.Counter()
    per_cand = collections.Counter()
    per_org = collections.Counter()
    per_month = collections.Counter()
    with gzip.open(os.path.join(root, "application.csv.gz"), "rt", encoding="utf-8", newline="") as h:
        for r in csv.DictReader(h):
            per_job[r["job_requirement_id"]] += 1
            per_cand[r["candidate_profile_id"]] += 1
            per_org[r["organisation_id"]] += 1
            per_month[r["applied_at"][:10]] += 1
    vals = sorted(per_job.values())
    out["apps_per_job"] = {"jobs": len(vals), "min": vals[0], "median": vals[len(vals) // 2],
                           "p95": vals[int(len(vals) * .95)], "max": vals[-1]}
    out["job_top10pct_share_of_apps"] = topshare(per_job, 0.1)
    out["candidates_with_app"] = len(per_cand)
    out["apps_per_candidate_max"] = max(per_cand.values())
    out["org_top10pct_share_of_apps"] = topshare(per_org, 0.1)
    days = sorted(per_month.items())
    out["applied_days"] = len(days)
    out["applied_day_range"] = [days[0][0], days[-1][0]]
    out["peak_day_over_median"] = round(max(per_month.values()) / sorted(per_month.values())[len(days) // 2], 2)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
