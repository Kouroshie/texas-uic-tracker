"""Screening checks on the public data.

Two kinds of result, kept apart everywhere in the app:
- "RRC record": something the RRC itself recorded in its database (an enforcement action with no compliance date,
  an H-10 violation with no resolved date, including the RRC's own 'delinquent H-10' violation code).
- "Screen": something this tool computes by comparing reported numbers with permit numbers. A screen hit is a
  question to look into, not a finding of a violation. Data entry errors, amended permits and permit terms that are
  not in the public file all produce false hits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from . import codes


@dataclass(frozen=True)
class Check:
    key: str
    title: str
    kind: str  # "RRC record" or "Screen"
    explain: str
    run: Callable[..., pd.DataFrame]


def in_service(w: pd.DataFrame) -> pd.Series:
    """Permit not cancelled and no plugging report (W-3) on file."""
    return w["cancelled"].isna() & w["w3_date"].isna()


def _ym_to_date(ym: pd.Series) -> pd.Series:
    ym = pd.Series(ym).astype("float")
    return pd.to_datetime(pd.DataFrame({"year": ym // 100, "month": ym % 100, "day": 1}), errors="coerce")


def _out(w: pd.DataFrame, hits: pd.DataFrame, check: str) -> pd.DataFrame:
    cols = ["uic", "operator", "operator_no", "district", "county", "lease", "well_no", "api"]
    if hits.empty:
        return pd.DataFrame(columns=cols + ["finding", "detail", "since", "check"])
    df = hits.merge(w[cols], on="uic", how="left")
    df["check"] = check
    return df[cols + ["finding", "detail", "since", "check"]].sort_values(["district", "operator", "uic"])


def open_enforcement(t: dict, as_of: pd.Timestamp) -> pd.DataFrame:
    e = t["enforcement"]
    e = e[e["compliance_date"].isna() & e["notice_date"].notna()
          & e["uic"].isin(t["wells"].loc[in_service(t["wells"]), "uic"])].copy()
    e["finding"] = "Enforcement action open: " + e["notice"].map(lambda c: codes.ENF_NOTICE.get(c, c))
    e["detail"] = ("Violation: " + e["violation"].map(lambda c: codes.ENF_VIOLATION.get(c, c))
                   + e["snc"].map({True: " (significant noncompliance)", False: ""})
                   + e["other"].map(lambda s: f"; {s}" if s else ""))
    e["since"] = e["notice_date"]
    return _out(t["wells"], e, "open_enforcement")


def open_h10_violations(t: dict, as_of: pd.Timestamp, years: int = 3) -> pd.DataFrame:
    """Only the last `years` reporting years: a check of older ones against the RRC's online H-10 violation query
    (2026-11) found them resolved there while the monthly file still showed them open."""
    v = t["h10_violations"]
    v = v[v["resolved_date"].isna() & (v["code"] != "12") & (v["cycle_start"] // 100 >= as_of.year - years)
          & v["uic"].isin(t["wells"].loc[in_service(t["wells"]), "uic"])].copy()
    v["finding"] = "H-10 violation unresolved: " + v["code"].map(lambda c: codes.H10_VIOLATION.get(c, c))
    v["detail"] = ("Reporting year " + (v["cycle_start"] // 100).astype(str)
                   + v["cert_letter_date"].map(lambda d: f"; certified letter {d[:4]}-{d[4:6]}-{d[6:]}"
                                               if isinstance(d, str) and d else "")
                   + v["severance_letter_date"].map(lambda d: "" if pd.isna(d) else f"; severance {d:%Y-%m-%d}"))
    v["since"] = v["letter_date"]
    return _out(t["wells"], v, "open_h10_violations")


def h5_overdue(t: dict, as_of: pd.Timestamp, grace_days: int = 30) -> pd.DataFrame:
    """Only each well's latest H-5 schedule counts: old schedules from the 1980s and 1990s were often never closed
    in the database even though a later test was filed."""
    w = t["wells"]
    h = t["h5"].sort_values(["due", "scheduled"], na_position="first").drop_duplicates("uic", keep="last")
    h = h[h["scheduled_flag"].eq("Y") & h["due"].notna() & (h["due"] < as_of - pd.Timedelta(days=grace_days)) & h["received"].isna()
          & (h["test_date"].isna() | (h["test_date"] < h["scheduled"].fillna(h["due"])))]
    h = h[h["uic"].isin(w.loc[in_service(w), "uic"])].copy()
    h["finding"] = "Pressure test (H-5) past due"
    h["detail"] = (h["schedule_type"].map(lambda c: f"{codes.H5_SCHEDULE_TYPE.get(c, c)} test" if c else "Test")
                   + " due " + h["due"].dt.strftime("%Y-%m-%d"))
    h["since"] = h["due"]
    return _out(w, h, "h5_overdue")


def mit_failed(t: dict, as_of: pd.Timestamp) -> pd.DataFrame:
    w = t["wells"]
    h = t["h5"][["uic", "test_date", "result"]]
    h = h[h["test_date"].notna() & h["result"].isin(["P", "F", "I"])].sort_values("test_date")
    last = h.drop_duplicates("uic", keep="last")
    last = last[last["result"].isin(["F", "I"]) & last["uic"].isin(w.loc[in_service(w), "uic"])].copy()
    last["finding"] = "Latest pressure test " + last["result"].map(codes.H5_RESULT).str.lower()
    last["detail"] = "Tested " + last["test_date"].dt.strftime("%Y-%m-%d") + "; no later passing test on file"
    last["since"] = last["test_date"]
    return _out(w, last, "mit_failed")


def mit_old(t: dict, as_of: pd.Timestamp, years: int = 5) -> pd.DataFrame:
    w = t["wells"]
    act = w[in_service(w) & w["h10_status"].eq("3")]
    h = t["h5"]
    h = h[h["test_date"].notna() & h["result"].eq("P")]
    last = h.groupby("uic", as_index=False)["test_date"].max()
    df = act[["uic"]].merge(last, on="uic", how="left")
    cutoff = as_of - pd.DateOffset(years=years)
    df = df[df["test_date"].isna() | (df["test_date"] < cutoff)].copy()
    df["finding"] = f"No passing pressure test in the last {years} years on file"
    df["detail"] = df["test_date"].map(lambda d: "No passing test on file" if pd.isna(d)
                                       else f"Last passing test {d:%Y-%m-%d}") + "; well reported active on H-10"
    df["since"] = df["test_date"]
    return _out(w, df, "mit_old")


def _recent(t: dict, months: int) -> pd.DataFrame:
    m = t["h10_recent"]
    last = int(m["ym"].max()) if len(m) else 0
    start = (_ym_to_date(pd.Series([last])).iloc[0] - pd.DateOffset(months=months - 1)) if last else None
    return m[_ym_to_date(m["ym"]) >= start] if start is not None else m.iloc[0:0]


def pressure_over_permit(t: dict, as_of: pd.Timestamp, months: int = 24, tolerance: int = 100) -> pd.DataFrame:
    """The limit is the higher of the two permitted pressures in the file (some permits list a second zone), and a
    month counts only when it is more than `tolerance` psig over, as in the RRC's own H-10 violation code 07."""
    w = t["wells"]
    lim = w[in_service(w)][["uic"]].assign(limit=w[["max_psi", "max_psi_2"]].max(axis=1))
    lim = lim[lim["limit"] > 0]
    m = _recent(t, months).merge(lim, on="uic")
    m = m[m["max_psi"] > m["limit"] + tolerance]
    if m.empty:
        return _out(w, m, "pressure_over_permit")
    g = m.groupby("uic", as_index=False).agg(n=("ym", "size"), worst=("max_psi", "max"), limit=("limit", "first"),
                                             first=("ym", "min"))
    g["finding"] = "Reported max injection pressure above the permitted maximum"
    g["detail"] = (g["n"].astype(str) + " month(s); highest " + g["worst"].astype(str) + " psig vs permit "
                   + g["limit"].astype(str) + " psig")
    g["since"] = _ym_to_date(g["first"])
    return _out(w, g, "pressure_over_permit")


def volume_over_permit(t: dict, as_of: pd.Timestamp, months: int = 24) -> pd.DataFrame:
    w = t["wells"]
    lim = w[in_service(w) & ((w["max_bbl_day"] > 0) | (w["max_mcf_day"] > 0))][["uic", "max_bbl_day", "max_mcf_day"]]
    m = _recent(t, months).merge(lim, on="uic")
    days = _ym_to_date(m["ym"]).dt.days_in_month
    over_bbl = (m["max_bbl_day"] > 0) & (m["bbl"] > m["max_bbl_day"] * days)
    over_mcf = (m["max_mcf_day"] > 0) & (m["mcf"] > m["max_mcf_day"] * days)
    m = m.assign(rate_bbl=(m["bbl"] / days).round(), rate_mcf=(m["mcf"] / days).round())[over_bbl | over_mcf]
    if m.empty:
        return _out(w, m, "volume_over_permit")
    g = m.groupby("uic", as_index=False).agg(n=("ym", "size"), bbl=("rate_bbl", "max"), mcf=("rate_mcf", "max"),
                                             lb=("max_bbl_day", "first"), lm=("max_mcf_day", "first"),
                                             first=("ym", "min"))
    g["finding"] = "Average daily volume above the permitted daily maximum"
    g["detail"] = g.apply(lambda r: f"{r.n} month(s); " + "; ".join(
        x for x in (f"up to {int(r.bbl):,} bbl/day vs permit {int(r.lb):,}" if r.lb and r.bbl > r.lb else "",
                    f"up to {int(r.mcf):,} Mcf/day vs permit {int(r.lm):,}" if r.lm and r.mcf > r.lm else "") if x),
        axis=1)
    g["since"] = _ym_to_date(g["first"])
    return _out(w, g, "volume_over_permit")


def injecting_without_completion(t: dict, as_of: pd.Timestamp, months: int = 24) -> pd.DataFrame:
    w = t["wells"]
    no = w[in_service(w) & w["w2g1_date"].isna()][["uic"]]
    m = _recent(t, months)
    m = m[(m["bbl"] > 0) | (m["mcf"] > 0)].merge(no, on="uic")
    if m.empty:
        return _out(w, m, "injecting_without_completion")
    g = m.groupby("uic", as_index=False).agg(n=("ym", "size"), first=("ym", "min"))
    g["finding"] = "Injection reported but no completion report (W-2/G-1) on file"
    g["detail"] = g["n"].astype(str) + " month(s) with volumes"
    g["since"] = _ym_to_date(g["first"])
    return _out(w, g, "injecting_without_completion")


def injecting_after_end(t: dict, as_of: pd.Timestamp, months: int = 24) -> pd.DataFrame:
    w = t["wells"]
    ended = w[w["cancelled"].notna() | w["w3_date"].notna()][["uic", "cancelled", "w3_date"]].copy()
    ended["end"] = ended[["cancelled", "w3_date"]].min(axis=1)
    m = _recent(t, months)
    m = m[(m["bbl"] > 0) | (m["mcf"] > 0)].merge(ended, on="uic")
    m = m[_ym_to_date(m["ym"]) > m["end"]]
    if m.empty:
        return _out(w, m, "injecting_after_end")
    g = m.groupby("uic", as_index=False).agg(n=("ym", "size"), first=("ym", "min"), end=("end", "first"))
    g["finding"] = "Injection reported after the permit was cancelled or the well plugged"
    g["detail"] = g["n"].astype(str) + " month(s) after " + g["end"].dt.strftime("%Y-%m-%d")
    g["since"] = _ym_to_date(g["first"])
    return _out(w, g, "injecting_after_end")


def no_recent_h10(t: dict, as_of: pd.Timestamp, years: int = 2) -> pd.DataFrame:
    w = t["wells"]
    latest_year = int(t["h10_recent"]["ym"].max()) // 100 if len(t["h10_recent"]) else as_of.year
    cutoff = (latest_year - years) * 100 + 12
    d = w[in_service(w) & w["activated"] & w["w2g1_date"].notna() & w["uic_class"].eq("2")
          & (w["last_h10_ym"].isna() | (w["last_h10_ym"] <= cutoff))].copy()
    d["finding"] = f"No H-10 monthly data in the last {years} reporting years"
    d["detail"] = d["last_h10_ym"].map(lambda v: "No H-10 data on file" if pd.isna(v)
                                       else f"Latest H-10 month {int(v) // 100}-{int(v) % 100:02d}")
    d["since"] = _ym_to_date(d["last_h10_ym"]).values
    return _out(w, d[["uic", "finding", "detail", "since"]], "no_recent_h10")


def texnet_stale(t: dict, as_of: pd.Timestamp, days: int = 90) -> pd.DataFrame:
    w = t["wells"]
    if "texnet_last" not in w:
        return _out(w, w.iloc[0:0], "texnet_stale")
    d = w[in_service(w) & w["texnet_last"].notna() & (w["texnet_last"] < as_of - pd.Timedelta(days=days))].copy()
    d["finding"] = f"No TexNet daily injection data in the last {days} days"
    d["detail"] = "Last TexNet day " + d["texnet_last"].dt.strftime("%Y-%m-%d")
    d["since"] = d["texnet_last"]
    return _out(w, d[["uic", "finding", "detail", "since"]], "texnet_stale")


CHECKS = [
    Check("open_enforcement", "Open enforcement actions", "RRC record",
          "Enforcement actions in the RRC's UIC database with no compliance date, on permits still in service.", open_enforcement),
    Check("open_h10_violations", "Unresolved H-10 violations", "Screen",
          "H-10 violations in the RRC's monthly database file with no resolved date, for the last 3 reporting years, "
          "on permits still in service (code 12, well not required to file, is left out). The RRC's online H-10 "
          "violation query is the current record and may already show one resolved.", open_h10_violations),
    Check("h5_overdue", "Pressure tests (H-5) past due", "Screen",
          "The well's latest H-5 schedule is open, its due date is more than 30 days before the data snapshot, and "
          "no H-5 is recorded as received. Read from the RRC's schedule fields; older open schedules are ignored.", h5_overdue),
    Check("mit_failed", "Latest pressure test failed or inconclusive", "Screen",
          "The most recent H-5 test on file failed or was inconclusive and no later test passed.", mit_failed),
    Check("pressure_over_permit", "Pressure above permit", "Screen",
          "A month on the H-10 where the reported maximum injection pressure is more than 100 psig above the permitted "
          "maximum surface pressure (the higher of the two limits in the file, the same margin the RRC's H-10 "
          "violation code 07 uses). Amended limits not yet in the file can cause false hits.",
          pressure_over_permit),
    Check("volume_over_permit", "Volume above permit", "Screen",
          "A month where the reported volume divided by the days in the month (the average daily rate) is above "
          "the permitted maximum daily volume. If the average is over, at least one day was over.",
          volume_over_permit),
    Check("mit_old", "No passing pressure test in 5 years", "Screen",
          "Wells reported active on their latest H-10 with no passing H-5 test dated in the last 5 years. Some "
          "wells use annulus monitoring or an alternate test instead.", mit_old),
    Check("no_recent_h10", "No recent H-10 data", "Screen",
          "Activated, completed injection/disposal wells (class 2) still in service with no H-10 monthly data in "
          "the last 2 reporting years.", no_recent_h10),
    Check("injecting_without_completion", "Injecting without a completion report", "Screen",
          "H-10 volumes reported in the last 24 months but no W-2/G-1 date on file.", injecting_without_completion),
    Check("injecting_after_end", "Injecting after cancel or plugging", "Screen",
          "H-10 volumes reported for months after the permit cancel date or the W-3 plugging date.",
          injecting_after_end),
    Check("texnet_stale", "TexNet reporting gap", "Screen",
          "Wells that report daily injection to TexNet whose most recent TexNet day is more than 90 days old. A "
          "well that is shut in can show here without any problem.", texnet_stale),
]
BY_KEY = {c.key: c for c in CHECKS}
