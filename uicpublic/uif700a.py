"""Read the RRC's public UIC database file (uif700a.txt.gz, ASCII, updated monthly) into tables.

Source: Railroad Commission of Texas, "Data Sets Available for Download", UIC Database, ASCII format.
Record layouts: RRC manual UIA010 and the layout files published with the data (uif700a.uimnh10_layout).
Each well starts with a root record (01); the records after it, up to the next 01, belong to that well.
Positions below are 0-based Python slices of the manual's 1-based positions.
"""
from __future__ import annotations

import gzip
import io
from array import array
from pathlib import Path

import pandas as pd

from .counties import COUNTIES

# The file stores RRC districts as numbers; these are the district names people use (checked by county:
# Ector is "10" = District 08, Wichita "13" = 09, Hutchinson "14" = 10, Scurry "11" = 8A).
DISTRICTS = {"01": "01", "02": "02", "03": "03", "04": "04", "05": "05", "06": "06", "07": "6E", "08": "7B",
             "09": "7C", "10": "08", "11": "8A", "12": "8B", "13": "09", "14": "10"}
KNOWN = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14"}


def _s(line: str, a: int, b: int) -> str:
    return line[a:b].strip()


def _t(line: str, a: int, b: int) -> str:
    """Free text; empty fields are stored as zeros in some records."""
    v = line[a:b].strip()
    return "" if not v.strip("0") else v


def _i(line: str, a: int, b: int) -> int:
    v = line[a:b].strip()
    return int(v) if v.isdigit() else 0


def _d(line: str, a: int, b: int):
    """CCYYMMDD text, or None for zeros, blanks and impossible dates."""
    v = line[a:b]
    if not v.isdigit() or v == "0" * len(v) or v[4:6] in ("00",) or not ("01" <= v[4:6] <= "12"):
        return None
    if len(v) == 8 and not ("01" <= v[6:8] <= "31"):
        return None
    return v


def parse(lines, log=print) -> dict[str, pd.DataFrame]:
    """Tables from the lines of uif700a.txt. Lines that do not start a known record are skipped, except the
    pieces of a remark split by a stray line break, which are joined back to the remark."""
    wells, monitor, h5, enf, h10v, remarks, enf_remarks = [], [], [], [], [], [], []
    m_uic, m_ym, m_avg, m_max, m_bbl, m_mcf = (array("i") for _ in range(6))
    uic = None
    uic_n = 0
    prev_short_remark = False
    skipped = 0
    for n, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        k = line[:2]
        if prev_short_remark and remarks and k not in KNOWN | {"00"}:
            remarks[-1]["text"] = (remarks[-1]["text"] + " " + line.strip()).strip()
            prev_short_remark = False
            continue
        prev_short_remark = False
        if k not in KNOWN:
            skipped += 1
            continue
        if k == "01":
            uic = line[2:11]
            uic_n = int(uic) if uic.isdigit() else 0
            wells.append(_root(line))
            continue
        if uic is None:
            skipped += 1
            continue
        if k == "04":
            m_uic.append(uic_n)
            m_ym.append(_i(line, 2, 8))
            m_avg.append(_i(line, 8, 12))
            m_max.append(_i(line, 12, 16))
            m_bbl.append(_i(line, 16, 24))
            m_mcf.append(_i(line, 24, 32))
        elif k == "02":
            remarks.append({"uic": uic, "remark_no": _i(line, 2, 5), "line_no": _i(line, 5, 7),
                            "text": line[9:69].strip(), "by": _s(line, 69, 72), "date": _d(line, 72, 80)})
            prev_short_remark = len(line) < 80
        elif k == "03":
            monitor.append(_monitor(uic, line))
        elif k == "07":
            h5.append(_h5(uic, line))
        elif k == "10":
            enf.append({"uic": uic, "violation_date": _d(line, 2, 10), "violation": line[10:12],
                        "notice_date": _d(line, 12, 20), "notice": line[20:22], "compliance_date": _d(line, 22, 30),
                        "compliance_method": line[30:32], "snc": line[32:33] == "Y", "other": ""})
        elif k == "11" and enf:
            other = " ".join(x for x in (_s(line, 2, 6), _s(line, 6, 11), _s(line, 11, 21)) if x)
            if enf[-1]["uic"] == uic:
                enf[-1]["other"] = other
        elif k == "12":
            enf_remarks.append({"uic": uic, "text": line[4:67].strip()})
        elif k == "14":
            key = _i(line, 41, 49)
            cert = str(99999999 - key) if key else None
            h10v.append({"uic": uic, "cycle_start": _i(line, 2, 8), "cycle_end": _i(line, 8, 14),
                         "code": line[14:16], "letter_date": _d(line, 24, 32), "resolved_date": _d(line, 32, 40),
                         "resolved_by": line[40:41].strip(),
                         "cert_letter_date": cert if cert and _d(cert, 0, 8) else None,
                         "severance_letter_date": _d(line, 53, 61)})
        if n and n % 5_000_000 == 0:
            log(f"  {n:,} lines read")
    log(f"  {len(wells):,} wells; {len(m_uic):,} H-10 monthly rows; {skipped:,} lines skipped")
    out = {
        "wells": pd.DataFrame(wells),
        "monitor": pd.DataFrame(monitor),
        "h10_monthly": pd.DataFrame({"uic": m_uic, "ym": m_ym, "avg_psi": m_avg, "max_psi": m_max,
                                     "bbl": m_bbl, "mcf": m_mcf}),
        "h5": pd.DataFrame(h5),
        "enforcement": pd.DataFrame(enf),
        "h10_violations": pd.DataFrame(h10v),
        "remarks": pd.DataFrame(remarks),
        "enforcement_remarks": pd.DataFrame(enf_remarks),
    }
    for name, df in out.items():
        for c in df.columns:
            if c.endswith("date") or c in ("approved", "w14_date", "h1_date", "added", "cancelled", "w2g1_date",
                                           "w3_date", "due", "received", "scheduled", "second_notice",
                                           "test_date", "issued", "delinquent_notice"):
                df[c] = pd.to_datetime(df[c], format="%Y%m%d", errors="coerce")
    return out


def _root(line: str) -> dict:
    cnty = _i(line, 32, 35)
    api_no = _s(line, 35, 40)
    return {
        "uic": line[2:11],
        "oil_gas": _s(line, 11, 12),
        "lease": _s(line, 12, 18),
        "district": DISTRICTS.get(line[18:20], line[18:20].strip()),
        "well_no": _s(line, 20, 26),
        "operator_no": _s(line, 26, 32),
        "api": f"42-{cnty:03d}-{api_no}" if cnty and api_no.strip("0") else "",
        "county": COUNTIES.get(cnty, str(cnty) if cnty else ""),
        "field_no": _s(line, 40, 48),
        "uic_class": _s(line, 48, 49),
        "approved": _d(line, 49, 57),
        "w14_date": _d(line, 57, 65),
        "h1_date": _d(line, 65, 73),
        "added": _d(line, 81, 89),
        "activated": line[89:90] == "Y",
        "cancelled": _d(line, 90, 98),
        "w2g1_date": _d(line, 98, 106),
        "w3_date": _d(line, 106, 114),
        "inj_type": _s(line, 114, 115),
        "inj_type_comment": _t(line, 115, 145),
        "fluid_comment": _t(line, 145, 175),
        "max_bbl_day": _i(line, 175, 184),
        "max_mcf_day": _i(line, 184, 193),
        "top_ft": _i(line, 193, 198),
        "bottom_ft": _i(line, 198, 203),
        "max_psi": _i(line, 203, 208),
        "h1_no": _s(line, 208, 213),
        "w14_no": _s(line, 213, 218),
        "max_psi_2": _i(line, 232, 237),
        "location": _t(line, 364, 416),
        "special_conditions_note": _t(line, 520, 548),
        "docket": f"{_s(line, 559, 561)}-{_s(line, 563, 568)}" if _s(line, 563, 568).strip("0") else "",
    }


def _monitor(uic: str, line: str) -> dict:
    cc = _s(line, 106, 110)
    return {
        "uic": uic,
        "h10_status": _s(line, 2, 3),
        "h10_status_comment": _t(line, 209, 229),
        "h10_cycle_year": int(cc) if cc.isdigit() and int(cc) > 1900 else None,
        "h10_due_month": _i(line, 253, 255) or None,
        "h10_on_hold": line[73:74] == "Y",
        "issued": _d(line, 74, 82),
        "received": _d(line, 82, 90),
        "second_notice": _d(line, 90, 98),
        "delinquent_notice": _d(line, 98, 106),
    }


def _h5(uic: str, line: str) -> dict:
    return {
        "uic": uic,
        "due": _d(line, 12, 20),
        "received": _d(line, 20, 28),
        "schedule_type": _s(line, 28, 29),
        "scheduled_flag": _s(line, 29, 30),
        "scheduled": _d(line, 30, 38),
        "second_notice": _d(line, 38, 46),
        "packer_ft": _i(line, 53, 58),
        "test_date": _d(line, 58, 66),
        "test_type": _s(line, 83, 86),
        "alt_test": _s(line, 86, 87),
        "well_status": _s(line, 87, 88),
        "reason": _s(line, 111, 115),
        "witnessed": line[200:201] == "Y",
        "result": _s(line, 201, 202),
    }


def open_lines(path: Path):
    path = Path(path)
    if path.suffix == ".gz":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="latin-1", newline="")
    return open(path, encoding="latin-1", newline="")
