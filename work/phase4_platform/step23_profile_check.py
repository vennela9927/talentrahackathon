"""Step 23 exit check: generated volumes and distributions against the Step 13 profile, within tolerance.

Reads the valid rows of a generated dataset (planted defect lines excluded) and measures every target the
Step 13 workbook states for volume, skew, nulls, peaks and the application funnel.
Usage: step23_profile_check.py --data DIR [--json OUT]
"""
import argparse
import csv
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import read_json, write_json
from step24_reference import CITIES, FAMILIES, ROLES

TIER1 = {c[0] for c in CITIES if c[4]}
ROLE_FAMILY = {r[0]: r[1] for r in ROLES}


def load(data, name, batch="b001", usecols=None):
    """Valid rows of every part of one contract file in a batch (planted defect lines removed)."""
    exclude = {}
    with open(data / "expected_quarantine.csv", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            if r["batch"] == batch:
                exclude.setdefault(r["file"], set()).add(int(r["line"]))
    frames = []
    for path in sorted((data / batch).glob(f"{name}*.csv.gz")):
        df = pd.read_csv(path, usecols=usecols, dtype=str, na_values=["\\N"], keep_default_na=False,
                         on_bad_lines="skip", engine="python" if name == "candidates" else "c")
        if name == "candidates":
            # pandas skips malformed lines, so line numbers shift; planted candidates carry CAN-X keys instead
            df = df[~df["external_key"].str.startswith("CAN-X")]
        else:
            df = df[~pd.Series(np.arange(2, len(df) + 2), index=df.index).isin(exclude.get(path.name, set()))]
        frames.append(df)
    return pd.concat(frames) if frames else pd.DataFrame(columns=usecols)


def check(metric, target, tol, observed, source, kind="abs"):
    if kind == "abs":
        ok = abs(observed - target) <= tol
    elif kind == "rel":
        ok = abs(observed - target) <= tol * target
    elif kind == "max":
        ok = observed <= target
    else:
        ok = observed == target
    return {"metric": metric, "target": target, "tolerance": tol if kind in ("abs", "rel") else kind,
            "observed": round(float(observed), 4), "pass": bool(ok), "source": source}


def top_share(values, frac):
    v = np.sort(np.asarray(values, float))[::-1]
    return v[: max(1, int(len(v) * frac))].sum() / v.sum()


def profile_check(data):
    data = Path(data)
    m = read_json(data / "manifest.json")
    t = m["targets"]
    cand = load(data, "candidates", usecols=["external_key", "city_id", "headline", "birth_date",
                                             "preferred_language"])
    jobs = load(data, "jobs", usecols=["external_key", "organisation_id", "job_role_id", "city_id", "salary_min"])
    apps = load(data, "applications", usecols=["external_key", "candidate_key", "job_key", "organisation_key",
                                               "applied_at"])
    ev = pd.concat([load(data, "status_events", usecols=["application_key", "to_status"]),
                    load(data, "status_events", "b002", usecols=["application_key", "to_status"])])
    with gzip.open(data / "master" / "organisations.csv.gz", "rt", encoding="utf-8") as h:
        n_orgs = sum(1 for _ in h) - 1
    rows = []
    S13 = "Step 13 "
    rows += [check("Organisations", t["organisations"], 0, n_orgs, S13 + "scale profile / docket ratio", "eq"),
             check("Candidates", t["candidates"], 0, len(cand), S13 + "02_Scale profiles", "eq"),
             check("Jobs", t["jobs"], 0, len(jobs), S13 + "02_Scale profiles", "eq"),
             check("Applications", t["applications"], 0, len(apps), S13 + "02_Scale profiles", "eq")]

    jpo = jobs.groupby("organisation_id").size().reindex([str(i) for i in range(1, n_orgs + 1)], fill_value=0)
    rows += [check("Share of jobs posted by top 40% of organisations", 0.78, 0.03, top_share(jpo, 0.4),
                   S13 + "T174 R-18..20 (Pareto 80/20)"),
             check("Jobs per organisation, median", 3, 1, np.median(jpo), S13 + "T174 R-18..20"),
             check("Jobs per organisation, p95", 18, 4, np.percentile(jpo, 95), S13 + "T174 R-18..20"),
             check("Jobs per organisation, max", 250, None, jpo.max(), S13 + "T174 R-18..20", "max")]

    apj = apps.groupby("job_key").size().reindex(jobs["external_key"], fill_value=0)
    ratio = np.percentile(apj, 95) / max(1, np.median(apj))
    rows += [check("Applications per job, p95 / median", 280 / 45, 0.15, ratio,
                   S13 + "T174 R-23..26 shape (median 45, p95 280), scaled to the 5M/100k mean; see CHG-13-01", "rel"),
             check("Applications per job, max", 2500, None, apj.max(), S13 + "T174 R-23..26", "max"),
             check("Share of applications to top 10% of organisations", 0.60, 0.05,
                   top_share(apps.groupby("organisation_key").size().reindex([str(i) for i in range(1, n_orgs + 1)], fill_value=0), 0.1),
                   S13 + "03_Generation distributions: 10% organisations / 60% writes")]

    city = jobs["city_id"].dropna().astype(int)
    rows.append(check("Share of postings in the 8 Tier-1 cities", 0.68, 0.02, city.isin(TIER1).mean(),
                      S13 + "T174 R-21..22"))
    for label, s in [("candidate city", cand["city_id"]), ("candidate headline", cand["headline"]),
                     ("candidate birth date", cand["birth_date"]), ("job city", jobs["city_id"]),
                     ("job salary", jobs["salary_min"])]:
        rows.append(check(f"Null rate, {label}", 0.10, 0.02, s.isna().mean(),
                          S13 + "03_Generation distributions: optional columns 10% null"))

    days = apps["applied_at"].str[:10].value_counts()
    rows.append(check("Busiest day / median day (applications)", 2.5, 0.1, days.max() / days.median(),
                      S13 + "03_Generation distributions: peak traffic 2.5x"))
    weekday = pd.to_datetime(days.index).dayofweek
    per_wd = pd.Series(days.values, index=weekday).groupby(level=0).mean()
    rows.append(check("Weekday (Mon-Fri) / weekend daily volume", 1.5, 0.5, per_wd[:5].mean() / per_wd[5:].mean(),
                      S13 + "T176 seasonality (weekday peaks)"))

    reach = ev.groupby("to_status")["application_key"].nunique() / len(apps)
    for status, target in [("shortlisted", 0.28), ("interviewed", 0.14), ("offered", 0.05), ("joined", 0.03)]:
        rows.append(check(f"Funnel reach: {status}", target, 0.005, reach.get(status, 0), S13 + "T174 R-27..28"))
    epa = ev.groupby("application_key").size()
    rows += [check("Status events per application, min", 1, 0, epa.min(), S13 + "T174 R-27..28 (1/2/4/5)", "eq"),
             check("Status events per application, median", 2, 0, np.median(epa), S13 + "T174 R-27..28", "eq"),
             check("Status events per application, p95", 4, 0, np.percentile(epa, 95), S13 + "T174 R-27..28", "eq"),
             check("Status events per application, max", 5, 0, epa.max(), S13 + "T174 R-27..28", "eq")]

    pairs = apps.duplicated(["candidate_key", "job_key"]).sum()
    rows.append(check("Duplicate candidate/job pairs", 0, 0, pairs, "Step 21 uq_job_application_candidate_job", "eq"))
    lang = cand["preferred_language"].value_counts(normalize=True)
    for code, share in [("en", 0.60), ("hi", 0.25), ("ta", 0.15)]:
        rows.append(check(f"Language share {code}", share, 0.01, lang.get(code, 0), "Step 4 NFR-013; assumption"))
    fam = jobs["job_role_id"].astype(int).map(ROLE_FAMILY).value_counts(normalize=True)
    for code, _, share in FAMILIES:
        rows.append(check(f"Job family share {code}", share, 0.01, fam.get(code, 0),
                          "Step 22 15_Family funnel assumptions"))
    return {"profile": m["profile"], "seed": m["seed"], "checks": rows, "passed": sum(r["pass"] for r in rows),
            "total": len(rows), "pass": all(r["pass"] for r in rows)}


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--data", required=True, type=Path)
    a.add_argument("--json", type=Path)
    args = a.parse_args()
    r = profile_check(args.data)
    for c in r["checks"]:
        print(f"{'PASS' if c['pass'] else 'FAIL'}  {c['metric']}: observed {c['observed']} target {c['target']}"
              f" tol {c['tolerance']}")
    print(f"{r['passed']}/{r['total']} checks pass")
    if args.json:
        write_json(args.json, r)


if __name__ == "__main__":
    main()
