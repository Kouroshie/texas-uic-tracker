"""Help text for every page: a 'How to use this page' box plus the short tooltips shown behind the '?' icons.
Also works out which years each data set covers and the date window each check looks at."""
from __future__ import annotations

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------- tooltips ('?' icons)
TIP = {
    "wells_total": "Every UIC permit record in the RRC's UIC database file, including cancelled permits and plugged "
                   "wells. One row per UIC number.",
    "in_service": "Not cancelled, no plugging report (W-3) on file, and the latest H-10 does not report the well as "
                  "converted, cancelled, plugged or permit suspended.",
    "active": "Permits in service whose latest H-10 annual report gives the well status 'active'.",
    "with_results": "Wells that show up in at least one of the eleven checks below. One well can appear in several.",
    "check_table": "One row per check. 'Wells' counts distinct UIC numbers, 'Operators' counts distinct operator "
                   "numbers. Open the Screening checks page to see the wells.",
    "kind": "RRC record: the RRC entered it in its own database. Screen: this app worked it out by comparing reported "
            "numbers with permit numbers. A Screen result is a reason to look closer, not a violation.",
    "district_chart": "Dark bars: permits in service reported active on their latest H-10. Light bars: permits in "
                      "service with at least one check result.",
    "check_pick": "Each check lists the wells it found, with the date window it looked at. The count in brackets is "
                  "the number of wells.",
    "filters": "Narrow the list. Filters combine: district AND county AND operator.",
    "operator_text": "Type part of an operator name (for example HILCORP) or the 6-digit P-5 operator number.",
    "since": "The date the finding starts: the notice date, due date, test date or first month over the limit.",
    "well_query": "A 9-digit UIC number (leading zeros optional), an API number such as 42-135-08294 or its last 8 "
                  "digits, or a 6-digit lease number. A lease number can match several wells; pick one from the list.",
    "permit": "In service, cancelled (with the cancel date) or plugged (with the W-3 date).",
    "h10_status": "The well status reported on the latest H-10 annual monitoring report: for example active, "
                  "temporarily abandoned, shut in.",
    "max_psi": "Maximum surface injection pressure in the permit, in psig. Some permits list a second (gas) limit; "
               "the checks use the higher one.",
    "max_vol": "Maximum daily injection volume in the permit: bbl/day for liquids, Mcf/day for gas.",
    "h10_chart": "Monthly pressure and volume from the operator's H-10 reports. The flat line is the permit limit. "
                 "Volumes are shown as the average per day (monthly total divided by days in the month).",
    "years_shown": "How many years of monthly H-10 data the charts show, counting back from the latest month on file.",
    "h5": "Mechanical integrity (pressure) tests on the H-5 form: when each test was due, when it was done and the "
          "result. The newest schedule is on top.",
    "h10_violations": "Violations the RRC recorded for this well's H-10 annual reports, such as a late or missing "
                      "report or pressure above the permit. 'resolved_date' empty means the file shows it open.",
    "enforcement": "Enforcement actions the RRC recorded for this well: the violation, the notice sent (for example "
                   "severance) and the compliance date. Empty compliance date means the file shows it open.",
    "well_checks": "Every check that found this well, with its kind (RRC record or Screen).",
    "operators_table": "One row per operator with permits in service. Each check column counts that operator's wells "
                       "in the check. Click a row to list the operator's wells below.",
    "rrc_record_col": "Wells with at least one RRC record result (open enforcement action).",
}

# ---------------------------------------------------------------- page help boxes
PAGE = {
    "overview": """
**What this page shows.** A statewide summary of injection, disposal and storage well permits (UIC) in the RRC's
public database, and how many wells each check found.

**How to use it**
- The four numbers at the top count wells. Hover over the **?** next to each one for its definition.
- The **Check results** table lists all eleven checks. *Kind* tells you who reached the conclusion: the RRC itself
  (*RRC record*) or this app (*Screen*).
- The district chart compares permits reported active with permits that have a check result.
- To see the actual wells, go to **Screening checks**. To look up one well, go to **Well record**.

**Dates.** Everything is as of the RRC file date shown in the sidebar. See *What years the data covers* below.
""",
    "checks": """
**What this page shows.** The wells found by one check at a time.

**How to use it**
1. Pick a check in the **Check** box. The coloured box under it explains the rule and the date window it uses.
2. Narrow the list with **District**, **County** or **Operator**.
3. **Click any row** to open that well's full record.
4. Download the list as CSV or Excel. *All checks in one list* at the bottom gives every result together.

**Reading a result.** *Finding* is what was found, *Detail* gives the numbers, *Since* is when it started.
A *Screen* result can be wrong for ordinary reasons: a typing error on the report, an amended permit not yet in the
file, or permit terms that are not in the public data. Check the RRC's own records before acting.
""",
    "well": """
**What this page shows.** Everything in the public data for one well.

**How to use it**
- Type a UIC number, API number or lease number, then press Enter. Or click a row on another page.
- **Top numbers**: permit status, latest H-10 status and the permitted pressure and volume limits.
- **Details table**: the permit record (location, interval, dates, permit numbers, TexNet reporting).
- **Check results**: every check that found this well.
- **H-10 monthly injection**: pressure and volume by month against the permit limit. Use *Years shown* to zoom.
  *Monthly rows* has the numbers.
- **Pressure tests (H-5)**, **H-10 violations** and **Enforcement actions**: the RRC's records for this well, newest
  first.

**Check it at the source.** Use the links under the details table to open the RRC's own permit and H-10 queries.
""",
    "operators": """
**What this page shows.** Permits in service and check results grouped by operator.

**How to use it**
- The table is sorted by number of permits in service. Type in the box to find one operator by name or number.
- Each check has its own column with the number of that operator's wells it found. Scroll right to see them all.
- **Click a row** to list that operator's wells with a check result. Click one of those to open the well record.
- Download the table as CSV or Excel.

**Note.** A large operator naturally has more results. Compare the counts with *Permits in service*.
""",
    "about": """
**What this page shows.** Where the data comes from, which years it covers, how each check works and its limits.
Read *Two kinds of check result* before relying on anything in this app.
""",
}


def page_help(page: str) -> None:
    with st.expander("How to use this page", icon=":material/help:"):
        st.markdown(PAGE[page])


# ---------------------------------------------------------------- data coverage
def _span(years: pd.Series, last_year: int) -> tuple[int | None, int | None]:
    """First and last year with real data. Stray typo years (1900, 2098) are skipped: the first year counts only
    when it holds at least 0.1% of the records (and at least 20)."""
    y = pd.Series(years).dropna().astype(int)
    y = y[(y >= 1900) & (y <= last_year)]
    if y.empty:
        return None, None
    vc = y.value_counts().sort_index()
    ok = vc[vc >= max(20, 0.001 * len(y))]
    return int((ok if not ok.empty else vc).index.min()), int(vc.index.max())


@st.cache_resource(show_spinner=False)
def coverage(stamp: str) -> pd.DataFrame:
    from . import data, ui
    t, m = ui.get_tables(), data.meta()
    as_of = data.snapshot_date(m)
    w = t["wells"]
    h10y = pd.read_parquet(data.DATA_DIR / "h10_yearly.parquet", columns=["year"])["year"]
    lm = str(m.get("latest_h10_month", ""))
    rows = []

    def add(name, years, what, to=None):
        a, b = _span(years, as_of.year)
        rows.append({"Data": name, "From": str(a or ""), "To": to or str(b or ""), "What": what})

    add("Permits (date added to the RRC database)", w["added"].dt.year,
        "The RRC's UIC database started in 1981; older permits were entered then.")
    add("H-10 monthly injection reports", h10y,
        "Monthly pressure and volume reported on the annual H-10.", to=f"{lm[:4]}-{lm[4:]}" if lm else None)
    add("H-5 pressure tests", t["h5"]["test_date"].dt.year, "Test dates of mechanical integrity tests.")
    add("Enforcement actions", t["enforcement"]["violation_date"].dt.year, "Violation dates.")
    add("H-10 violations", t["h10_violations"]["cycle_start"] // 100, "H-10 reporting years with a violation.")
    if "texnet_first" in w:
        a, _ = _span(w["texnet_first"].dt.year, as_of.year)
        last = w["texnet_last"].max()
        rows.append({"Data": "TexNet daily injection (dates only)", "From": str(a or ""),
                     "To": "" if pd.isna(last) else f"{last:%Y-%m-%d}",
                     "What": "First and last day each well reported to TexNet."})
    rows.append({"Data": "Checks run as of", "From": "", "To": f"{as_of:%Y-%m-%d}",
                 "What": "The date the RRC lists for its monthly file."})
    return pd.DataFrame(rows)


def check_window(key: str, t: dict, as_of: pd.Timestamp) -> str:
    """The dates a check looks at, in words."""
    from .checks import last_month
    ym = last_month(t, as_of)
    last = pd.Timestamp(year=ym // 100, month=ym % 100, day=1) if ym else as_of
    start24 = last - pd.DateOffset(months=23)
    h10_24 = f"H-10 months {start24:%Y-%m} to {last:%Y-%m} (the latest 24 months on file up to the RRC file date)"
    d = lambda x: f"{x:%Y-%m-%d}"  # noqa: E731
    return {
        "open_enforcement": f"Enforcement notices dated {d(as_of - pd.DateOffset(years=10))} to {d(as_of)}.",
        "open_h10_violations": f"H-10 reporting years {as_of.year - 3} to {as_of.year}.",
        "h5_overdue": f"H-5 tests due {d(as_of - pd.DateOffset(years=10))} to {d(as_of - pd.Timedelta(days=30))}.",
        "mit_failed": "The latest H-5 test on file for each well, any year.",
        "pressure_over_permit": h10_24 + ".",
        "volume_over_permit": h10_24 + ".",
        "mit_old": f"Passing H-5 tests since {d(as_of - pd.DateOffset(years=5))}.",
        "no_recent_h10": f"No H-10 month in {last.year - 1} or {last.year}.",
        "injecting_without_completion": h10_24 + ".",
        "injecting_after_end": h10_24 + ".",
        "texnet_stale": f"Last TexNet day before {d(as_of - pd.Timedelta(days=90))}.",
    }.get(key, "")
