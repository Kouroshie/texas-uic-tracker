"""Shared bits for the Streamlit pages."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from .help import TIP as _TIP  # noqa: E402

RRC_PERMIT_QUERY = "https://webapps2.rrc.texas.gov/EWA/uicQueryAction.do"
RRC_H10_QUERY = "https://webapps.rrc.texas.gov/H10/searchH10.do"


@st.cache_resource(show_spinner="Loading the data...")
def _tables(stamp: str) -> dict:
    from . import data
    return data.load()


@st.cache_resource(show_spinner="Running the checks...")
def _checks(stamp: str) -> dict:
    """Results computed by the monthly build (checks.parquet); computed here when that file is missing."""
    from . import checks, data
    pre = data.DATA_DIR / "checks.parquet"
    if pre.exists():
        df = pd.read_parquet(pre)
        return {c.key: df[df["check"] == c.key].reset_index(drop=True) for c in checks.CHECKS}
    t = _tables(stamp)
    as_of = data.snapshot_date(data.meta())
    return {c.key: c.run(t, as_of) for c in checks.CHECKS}


def get_tables() -> dict:
    return _tables(st.session_state["stamp"])


def get_checks() -> dict:
    return _checks(st.session_state["stamp"])


def filters(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """District, county and operator filters above a table."""
    c1, c2, c3 = st.columns(3)
    dist = c1.multiselect("District", sorted(x for x in df["district"].dropna().unique() if x), key=f"{key}_d",
                          help="RRC oil and gas district (01 to 10, 6E, 7B, 7C, 8A). " + _TIP["filters"])
    cnty = c2.multiselect("County", sorted(x for x in df["county"].dropna().unique() if x), key=f"{key}_c",
                          help="County of the well. " + _TIP["filters"])
    oper = c3.text_input("Operator name or number contains", key=f"{key}_o", help=_TIP["operator_text"]).strip().upper()
    if dist:
        df = df[df["district"].isin(dist)]
    if cnty:
        df = df[df["county"].isin(cnty)]
    if oper:
        df = df[df["operator"].str.upper().str.contains(oper, regex=False, na=False)
                | df["operator_no"].astype(str).str.contains(oper, regex=False, na=False)]
    return df


def downloads(df: pd.DataFrame, name: str) -> None:
    c1, c2, _ = st.columns([1, 1, 4])
    c1.download_button("Download CSV", df.to_csv(index=False).encode(), f"{name}.csv", "text/csv",
                       key=f"csv_{name}")
    buf = io.BytesIO()
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.date
    out.to_excel(buf, index=False)
    c2.download_button("Download Excel", buf.getvalue(), f"{name}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"xlsx_{name}")


def well_table(df: pd.DataFrame, key: str) -> None:
    """A table whose rows open the well record when clicked."""
    ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      key=key, column_config={"since": st.column_config.DateColumn("Since", format="YYYY-MM-DD", help=_TIP["since"]),
                                     "uic": st.column_config.TextColumn("uic", help="UIC permit number. Click the row to open the well.")})
    rows = ev.selection.rows if ev and ev.selection else []
    if rows:
        st.session_state["well_query"] = df.iloc[rows[0]]["uic"]
        st.switch_page("views/well.py")
