"""Parser and check tests on synthetic fixed-width records (no download needed)."""
import pandas as pd

from build_data import recent_start
from uicpublic import checks, uif700a


def put(line: list, pos: int, text: str) -> None:
    """Write text at a 1-based manual position."""
    for i, ch in enumerate(text):
        line[pos - 1 + i] = ch


def rec(kind: str, fields: dict, width: int = 622) -> str:
    line = [" "] * width
    put(line, 1, kind)
    for pos, text in fields.items():
        put(line, pos, text)
    return "".join(line) + "\r\n"


ROOT = rec("01", {3: "000123456", 12: "O", 13: "012345", 19: "10", 21: "1     ", 27: "654321", 33: "003",
                  36: "12345", 49: "2", 50: "20100105", 90: "Y", 91: "00000000", 99: "20100601", 107: "00000000",
                  115: "1", 176: "000005000", 185: "000000000", 194: "05000", 199: "06000", 204: "01500"})
MONITOR = rec("03", {3: "3", 75: "20260101", 83: "00000000", 91: "20260415", 107: "2025", 254: "04"})
H10 = [rec("04", {3: "202601", 9: "1200", 13: "1700", 17: "00160000", 25: "00000000"}, 54),
       rec("04", {3: "202602", 9: "1100", 13: "1400", 17: "00100000", 25: "00000000"}, 54)]
H5 = rec("07", {13: "20250101", 21: "00000000", 29: "F", 30: "Y", 59: "20190301", 202: "P"})
ENF = rec("10", {3: "20250101", 11: "09", 13: "20250201", 21: "01", 23: "00000000", 31: "00", 33: "Y"})
H10V = rec("14", {3: "202401", 9: "202412", 15: "07", 25: "20250301", 33: "00000000"})
REMARK_SPLIT = ["0200101  SHORT REMARK\r\n", "CONTINUED TEXT\r\n"]


def tables():
    lines = [ROOT, *REMARK_SPLIT, MONITOR, *H10, H5, ENF, H10V, "\x0c\r\n"]
    t = uif700a.parse(lines, log=lambda *a: None)
    w = t["wells"].merge(t["monitor"], on="uic", how="left")
    w["operator"], w["texnet_last"], w["last_h10_ym"] = "TEST OPERATOR", pd.NaT, 202602
    m = t["h10_monthly"].assign(uic=lambda d: d["uic"].astype(str).str.zfill(9))
    return t | {"wells": w, "h10_recent": m}


def test_root_fields():
    w = tables()["wells"].iloc[0]
    assert (w["uic"], w["district"], w["lease"], w["operator_no"]) == ("000123456", "08", "012345", "654321")
    assert w["api"] == "42-003-12345" and w["county"] == "Andrews"
    assert (w["max_psi"], w["max_bbl_day"], w["top_ft"], w["bottom_ft"]) == (1500, 5000, 5000, 6000)
    assert w["approved"] == pd.Timestamp("2010-01-05") and pd.isna(w["cancelled"]) and w["activated"]


def test_split_remark_is_joined_and_formfeed_skipped():
    t = tables()
    assert t["remarks"]["text"].tolist() == ["SHORT REMARK CONTINUED TEXT"]
    assert len(t["h10_monthly"]) == 2


def test_rrc_record_checks():
    t, as_of = tables(), pd.Timestamp("2026-11-01")
    assert checks.open_enforcement(t, as_of)["detail"].str.contains("Injection pressure").all()
    assert len(checks.open_h10_violations(t, as_of)) == 1
    assert len(checks.h5_overdue(t, as_of)) == 1


def test_screens():
    t, as_of = tables(), pd.Timestamp("2026-11-01")
    p = checks.pressure_over_permit(t, as_of)
    assert len(p) == 1 and "1700 psig vs permit 1500" in p["detail"].iloc[0]
    assert checks.pressure_over_permit(t, as_of, tolerance=300).empty
    v = checks.volume_over_permit(t, as_of)  # Jan: 160,000 bbl / 31 days = 5,161 bbl/day > 5,000
    assert len(v) == 1 and v["detail"].iloc[0].startswith("1 month(s)")
    assert len(checks.mit_old(t, as_of)) == 1  # last passing test 2019
    assert checks.injecting_without_completion(t, as_of).empty
    assert checks.injecting_after_end(t, as_of).empty


def test_recent_start():
    assert recent_start(202609) == 202310
    assert recent_start(202601, 1) == 202601
