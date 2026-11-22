"""Load the prebuilt data folder; download it from the latest GitHub data release when it is missing."""
from __future__ import annotations

import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("UIC_DATA_DIR", ROOT / "data"))
DATA_URL = os.environ.get("UIC_DATA_URL",
                          "https://github.com/Kouroshie/texas-uic-tracker/releases/download/data/uic-data.zip")
TABLES = ["wells", "h10_recent", "h5", "enforcement", "h10_violations"]


FILES = TABLES + ["h10_monthly", "h10_yearly"]  # checks.parquet is optional


def have_data(folder: Path = DATA_DIR) -> bool:
    return (folder / "meta.json").exists() and all((folder / f"{t}.parquet").exists() for t in FILES)


def download(folder: Path = DATA_DIR, url: str = DATA_URL) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "texas-uic-tracker"})
    with urllib.request.urlopen(req, timeout=600) as r:
        blob = r.read()
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(folder)


def meta(folder: Path = DATA_DIR) -> dict:
    return json.loads((folder / "meta.json").read_text())


def _uic(s: pd.Series) -> pd.Series:
    return s.astype(str).str.zfill(9)


def load(folder: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    t = {name: pd.read_parquet(folder / f"{name}.parquet") for name in TABLES}
    for name in ("h10_recent",):
        t[name]["uic"] = _uic(t[name]["uic"])
    w = t["wells"]
    w["operator"] = w["operator"].fillna("(operator " + w["operator_no"] + ")")
    w["district"] = w["district"].fillna("")
    for c in ("inj_type_comment", "fluid_comment", "location", "special_conditions_note", "h10_status_comment"):
        if c in w:  # data built before zero-filled text was cleaned
            w[c] = w[c].fillna("").where(w[c].fillna("").str.strip("0 ") != "", "")
    return t


def well_months(uic: str, folder: Path = DATA_DIR) -> pd.DataFrame:
    """All H-10 months for one well. The file is sorted by UIC, so only the matching row group is read."""
    d = ds.dataset(folder / "h10_monthly.parquet")
    df = d.to_table(filter=ds.field("uic") == int(uic)).to_pandas()
    df["month"] = pd.to_datetime(df["ym"].astype(str) + "01", format="%Y%m%d")
    return df.sort_values("month")


def snapshot_date(m: dict) -> pd.Timestamp:
    """The date the RRC lists for its UIC file (for example '10/31/26 6:01:31 AM'). Checks are run as of this date,
    since nothing later can be in the file."""
    try:
        return pd.to_datetime(m["uic_database_listed"].split()[0], format="%m/%d/%y")
    except (KeyError, ValueError, AttributeError):
        return pd.Timestamp.today().normalize()


def stale(m: dict, days: int = 40) -> bool:
    try:
        return (pd.Timestamp.now(tz="UTC") - pd.Timestamp(m["built"].replace(" UTC", ""), tz="UTC")).days > days
    except (KeyError, ValueError):
        return False
