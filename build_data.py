"""Build the app's data folder from the public sources.

    python build_data.py               download what changed, then rebuild data/
    python build_data.py --raw DIR     keep the large downloads in DIR (default: ./raw)

Takes about 10 to 15 minutes and 3 GB of memory, mostly to read the 280 MB RRC UIC file. The GitHub workflow in
.github/workflows/data.yml runs this every month and publishes the result, so most people never need to.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from uicpublic import sources, uif700a

ROOT = Path(__file__).resolve().parent


def recent_start(last_ym: int, months: int = 36) -> int:
    y, mo = divmod(last_ym, 100)
    n = y * 12 + (mo - 1) - (months - 1)
    return (n // 12) * 100 + n % 12 + 1


def build(raw: Path, out: Path, log=print) -> dict:
    t0 = time.time()
    uic_file, uic_listed = sources.godrive_download(sources.UIC_LINK, "uif700a.txt.gz", raw, log=log)
    p5_file, p5_listed = sources.godrive_download(sources.P5_LINK, "orf850.txt.gz", raw, log=log)

    log("Reading the RRC UIC database...")
    with uif700a.open_lines(uic_file) as f:
        t = uif700a.parse(f, log=log)

    log("Reading P-5 operator names...")
    ops = sources.operators(p5_file)
    wells = t["wells"].merge(ops, on="operator_no", how="left")
    mon = t["monitor"].drop_duplicates("uic")
    wells = wells.merge(mon, on="uic", how="left")

    log("Reading TexNet injection wells...")
    try:
        tx = sources.texnet_wells()
        wells = wells.merge(tx, on="uic", how="left")
        texnet_note = f"{len(tx):,} wells"
    except Exception as e:  # TexNet down should not stop the monthly build
        log(f"  TexNet not reachable ({e}); building without it")
        texnet_note = "not reachable at build time"

    m = t["h10_monthly"]
    now_ym = datetime.now().year * 100 + datetime.now().month
    m = m[(m["ym"] // 100 >= 1950) & (m["ym"] % 100).between(1, 12) & (m["ym"] <= now_ym)]  # drop typo years
    yearly = (m.assign(year=m["ym"] // 100)
              .groupby(["uic", "year"], as_index=False)
              .agg(months=("ym", "nunique"), max_psi=("max_psi", "max"), total_bbl=("bbl", "sum"),
                   total_mcf=("mcf", "sum"), max_month_bbl=("bbl", "max"), max_month_mcf=("mcf", "max")))
    last = m.groupby("uic", as_index=False)["ym"].max().rename(columns={"ym": "last_h10_ym"})
    wells["uic_n"] = pd.to_numeric(wells["uic"], errors="coerce").astype("Int64")
    wells = wells.merge(last, left_on="uic_n", right_on="uic", how="left", suffixes=("", "_m")).drop(columns="uic_m")

    out.mkdir(parents=True, exist_ok=True)
    _drop_old(out)
    tables = {
        "wells": wells.drop(columns="uic_n"),
        "h10_monthly": m.sort_values(["uic", "ym"]).astype({"uic": "int32", "ym": "int32", "avg_psi": "int32",
                                                             "max_psi": "int32", "bbl": "int64", "mcf": "int64"}),
        "h10_yearly": yearly,
        # The last 36 months, what the screening checks read, so the app does not load all 20+ million rows.
        "h10_recent": m[m["ym"] >= recent_start(int(m["ym"].max()))].astype({"uic": "int32", "ym": "int32"}),
        "h5": t["h5"],
        "enforcement": t["enforcement"],
        "h10_violations": t["h10_violations"],
        # Remarks are left out on purpose: the RRC's free-text notes include people's phone numbers and emails.
    }
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False, compression="zstd",
                      row_group_size=500_000 if name == "h10_monthly" else None)
        log(f"  {name}: {len(df):,} rows, {(out / f'{name}.parquet').stat().st_size / 1e6:.1f} MB")
    per_month = m.groupby("ym").size()
    log("Running the checks...")
    from uicpublic import checks, data
    as_of = data.snapshot_date({"uic_database_listed": uic_listed})
    t2 = data.load(out)
    res = pd.concat([c.run(t2, as_of) for c in checks.CHECKS], ignore_index=True)
    res.to_parquet(out / "checks.parquet", index=False, compression="zstd")
    log(f"  checks: {len(res):,} rows")
    meta = {
        "checks_as_of": f"{as_of:%Y-%m-%d}",
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "uic_database_listed": uic_listed,
        "p5_listed": p5_listed,
        "texnet": texnet_note,
        # The latest month with a real share of reports (a few reports arrive early for the current month).
        "latest_h10_month": int(per_month[per_month >= 0.01 * per_month.max()].index.max()) if len(m) else None,
        "wells": int(len(wells)),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    log(f"Done in {(time.time() - t0) / 60:.1f} min: {out}")
    return meta


if __name__ == "__main__":
    args = sys.argv[1:]
    raw = Path(args[args.index("--raw") + 1]) if "--raw" in args else ROOT / "raw"
    build(raw, ROOT / "data")


def _drop_old(out: Path) -> None:
    for name in ("remarks", "enforcement_remarks"):
        (out / f"{name}.parquet").unlink(missing_ok=True)
