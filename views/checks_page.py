import pandas as pd
import streamlit as st

from uicpublic import checks, ui

res = ui.get_checks()

st.title("Screening checks")
st.write("Pick a check. Click a row to open that well's record. Use the filters to narrow to a district, county or "
         "operator, then download the list.")

labels = {c.key: f"{c.title}  ({res[c.key]['uic'].nunique():,} wells, {c.kind})" for c in checks.CHECKS}
key = st.selectbox("Check", list(labels), format_func=labels.get, key="check")
chk = checks.BY_KEY[key]
if chk.kind == "Screen":
    st.warning(f"**Screen.** {chk.explain}", icon=":material/troubleshoot:")
else:
    st.info(f"**RRC record.** {chk.explain}", icon=":material/fact_check:")

df = ui.filters(res[key], key)
st.caption(f"{len(df):,} rows, {df['uic'].nunique():,} wells, {df['operator_no'].nunique():,} operators")
show = df.drop(columns=["check"]).rename(columns={"uic": "UIC", "operator": "Operator", "operator_no": "Operator no.",
                                                  "district": "District", "county": "County", "lease": "Lease",
                                                  "well_no": "Well", "api": "API", "finding": "Finding",
                                                  "detail": "Detail", "since": "since"})
show = show.rename(columns={"UIC": "uic"})
ui.well_table(show, f"tbl_{key}")
ui.downloads(df.drop(columns=["check"]), f"uic_{key}")

with st.expander("All checks in one list"):
    every = pd.concat(res.values(), ignore_index=True)
    every["check"] = every["check"].map(lambda k: checks.BY_KEY[k].title)
    every = ui.filters(every, "all")
    st.caption(f"{len(every):,} rows, {every['uic'].nunique():,} wells")
    ui.downloads(every, "uic_all_checks")
