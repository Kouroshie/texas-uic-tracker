"""Downloads of the public data the app uses. No logins, no keys.

- RRC UIC database (uif700a.txt.gz) and P-5 organization file (orf850.txt.gz): the RRC's managed file transfer
  "GoDrive" links listed on https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/
- TexNet injection wells: the Bureau of Economic Geology's public ArcGIS service.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

import pandas as pd

UIC_LINK = "https://mft.rrc.texas.gov/link/d2438c05-b42f-45a8-b0c6-edceb0912767"
P5_LINK = "https://mft.rrc.texas.gov/link/04652169-eed6-4396-9019-2e270e790f6c"
TEXNET_WELLS = ("https://maps.texnet.beg.utexas.edu/arcgis/rest/services/injection/Injection/MapServer/0/query")
USER_AGENT = "texas-uic-tracker"


def _opener():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    op.addheaders = [("User-Agent", USER_AGENT)]
    return op


def godrive_download(link: str, name: str, dest: Path, log=print, timeout: int = 300) -> tuple[Path, str]:
    """Download one file from an RRC GoDrive link page. Returns (path, the date the page lists). Skips the
    download when the same listed date was downloaded before."""
    dest.mkdir(parents=True, exist_ok=True)
    op = _opener()
    page = op.open(link, timeout=timeout).read().decode("utf-8", "replace")
    form = re.search(r'<form id="fileList".*?</form>', page, re.S)
    if not form:
        raise RuntimeError(f"the RRC download page {link} has changed (no file list)")
    form = form.group(0)
    row = next((r for r in re.findall(r"<tr[^>]*data-ri=\"\d+\"[^>]*>(.*?)</tr>", form, re.S)
                if f">{name}<" in r), None)
    if not row:
        raise RuntimeError(f"{name} is not listed on {link}")
    link_id = re.search(r'id="(fileTable:\d+:[^"]+)"', row).group(1)
    listed = re.sub(r"<[^>]+>", "", re.search(r'ModifiedOnColumn">(.*?)</td>', row, re.S).group(1)).strip()
    out = dest / name
    stamp = dest / (name + ".listed")
    if out.exists() and stamp.exists() and stamp.read_text().strip() == listed:
        log(f"{name}: already have the copy listed {listed}")
        return out, listed
    fields = {m.group(1): html.unescape(m.group(2))
              for m in re.finditer(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', form)}
    fields.update({"fileList": "fileList", link_id: link_id})
    action = urllib.parse.urljoin(link, re.search(r'action="([^"]+)"', form).group(1))
    req = urllib.request.Request(action, data=urllib.parse.urlencode(fields).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": link})
    log(f"{name}: downloading the copy listed {listed}...")
    tmp = out.with_name(out.name + ".part")
    with op.open(req, timeout=timeout) as r, open(tmp, "wb") as f:
        if "html" in (r.headers.get("Content-Type") or ""):
            raise RuntimeError(f"{name}: the RRC page answered with a web page instead of the file")
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(out)
    stamp.write_text(listed)
    return out, listed


def operators(path: Path) -> pd.DataFrame:
    """Operator number -> name and P-5 status, from the 'A ' records of orf850 (P-5 manual ORA001)."""
    import gzip
    rows = []
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="latin-1", newline="") as f:
        for line in f:
            if line[:2] == "A " and line[2:8].isdigit():
                rows.append((line[2:8], line[8:40].strip(), line[41:42].strip()))
    return pd.DataFrame(rows, columns=["operator_no", "operator", "p5_status"]).drop_duplicates("operator_no")


def texnet_wells(timeout: int = 60) -> pd.DataFrame:
    """Wells that report daily injection to TexNet, with the first and last injection dates."""
    op = _opener()
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"where": "1=1", "outFields": "UICNumber,FirstInjection,LastInjection,InjectionCount",
                                    "returnGeometry": "false", "resultOffset": offset,
                                    "resultRecordCount": 1000, "f": "json"})
        data = json.loads(op.open(f"{TEXNET_WELLS}?{q}", timeout=timeout).read())
        feats = data.get("features") or []
        rows += [f["attributes"] for f in feats]
        if not data.get("exceededTransferLimit") and len(feats) < 1000:
            break
        offset += len(feats)
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["uic", "texnet_first", "texnet_last", "texnet_days"])
    df["uic"] = df["UICNumber"].astype(str).str.strip().str.zfill(9)
    for a, b in (("FirstInjection", "texnet_first"), ("LastInjection", "texnet_last")):
        df[b] = pd.to_datetime(df[a], unit="ms", errors="coerce").dt.normalize()
    df["texnet_days"] = df["InjectionCount"]
    return df[["uic", "texnet_first", "texnet_last", "texnet_days"]].drop_duplicates("uic")
