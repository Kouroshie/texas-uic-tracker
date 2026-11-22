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
TABLES = ["wells", "h10_recent", "h5", "enforcement", "h10_violations", "enforcement_remarks"]


FILES = TABLES + ["h10_monthly", "h10_yearly", "remarks"]  # checks.parquet is optional


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
    return t


def well_months(uic: str, folder: Path = DATA_DIR) -> pd.DataFrame:
    """All H-10 months for one well. The file is sorted by UIC, so only the matching row group is read."""
    d = ds.dataset(folder / "h10_monthly.parquet")
    df = d.to_table(filter=ds.field("uic") == int(uic)).to_pandas()
    df["month"] = pd.to_datetime(df["ym"].astype(str) + "01", format="%Y%m%d")
    return df.sort_values("month")


def well_remarks(uic: str, folder: Path = DATA_DIR) -> pd.DataFrame:
    path = folder / "remarks.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["remark_no", "line_no", "text", "by", "date"])
    df = ds.dataset(path).to_table(filter=ds.field("uic") == uic).to_pandas()
    return df.sort_values(["remark_no", "line_no"])
