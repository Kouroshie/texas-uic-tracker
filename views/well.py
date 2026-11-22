import pandas as pd
import streamlit as st

from uicpublic import checks, codes, data, ui

t = ui.get_tables()
res = ui.get_checks()
w = t["wells"]

st.title("Well record")
q = st.text_input("UIC number, API number (42-ccc-nnnnn or 8 digits), or lease number", key="well_query").strip()
if not q:
    st.write("Enter a number above, or click a row on the Screening checks page.")
    st.stop()

digits = "".join(ch for ch in q if ch.isdigit())
hit = w[w["uic"] == digits.zfill(9)] if digits and len(digits) <= 9 else w.iloc[0:0]
if hit.empty and digits:
    api = w["api"].str.replace("-", "").str[2:]
    hit = w[(api == digits[-8:]) | (w["lease"] == digits.zfill(6))]
if hit.empty:
    st.warning("No well found.")
    st.stop()
if len(hit) > 1:
    pick = st.selectbox("More than one well matches", hit["uic"],
                        format_func=lambda u: f"UIC {u}: " + " ".join(
                            str(x) for x in hit.loc[hit['uic'] == u, ['operator', 'lease', 'well_no']].iloc[0]))
    hit = hit[hit["uic"] == pick]
r = hit.iloc[0]
uic = r["uic"]


def d(v):
    return "" if pd.isna(v) else f"{v:%Y-%m-%d}"


status = "Cancelled " + d(r["cancelled"]) if pd.notna(r["cancelled"]) else (
    "Plugged (W-3) " + d(r["w3_date"]) if pd.notna(r["w3_date"]) else "In service")
st.subheader(f"UIC {uic}: {r['operator']}, lease {r['lease']} well {r['well_no']}")
c = st.columns(4)
c[0].metric("Permit", status)
c[1].metric("Latest H-10 status", codes.WELL_STATUS.get(str(r.get("h10_status") or ""), "None on file"))
c[2].metric("Max surface pressure (permit)", f"{int(r['max_psi']):,} psig" if r["max_psi"] else "Not in file")
c[3].metric("Max daily volume (permit)", " / ".join(x for x in (
    f"{int(r['max_bbl_day']):,} bbl" if r["max_bbl_day"] else "", f"{int(r['max_mcf_day']):,} Mcf"
    if r["max_mcf_day"] else "") if x) or "Not in file")

info = {
    "API": r["api"], "District": r["district"], "County": r["county"], "Oil or gas lease": r["oil_gas"],
    "Operator": f"{r['operator']} ({r['operator_no']})", "P-5 status": r.get("p5_status") or "",
    "UIC class": codes.UIC_CLASS.get(r["uic_class"], r["uic_class"]),
    "Injection type": codes.INJ_TYPE.get(r["inj_type"], r["inj_type"]) + (
        f" ({r['inj_type_comment']})" if r["inj_type_comment"] else ""),
    "Fluid": r["fluid_comment"], "Injection interval": f"{r['top_ft']:,} to {r['bottom_ft']:,} ft"
    if r["top_ft"] else "", "Permit approved": d(r["approved"]), "W-14 / H-1 permit no.":
    " / ".join(x for x in (r["w14_no"], r["h1_no"]) if x and x.strip("0")),
    "Completion (W-2/G-1)": d(r["w2g1_date"]), "Docket": r["docket"], "Location": r["location"],
    "Special conditions note": r["special_conditions_note"],
    "H-10 year / due month": f"{'' if pd.isna(r['h10_cycle_year']) else int(r['h10_cycle_year'])} / "
                              f"{'' if pd.isna(r['h10_due_month']) else int(r['h10_due_month'])}",
    "H-10 issued / second notice / received": f"{d(r['issued'])} / {d(r['second_notice'])} / {d(r['received'])}",
    "TexNet daily reporting": (f"{d(r['texnet_first'])} to {d(r['texnet_last'])}"
                               if "texnet_last" in r and pd.notna(r["texnet_last"]) else "Not in TexNet"),
}
st.dataframe(pd.DataFrame({"Item": info.keys(), "Value": [str(v) for v in info.values()]}), hide_index=True,
             width="stretch")
st.caption(f"Check the RRC's own records: [Injection-Storage Permit Query]({ui.RRC_PERMIT_QUERY}) and "
           f"[H-10 Filing Query]({ui.RRC_H10_QUERY}), UIC {uic}.")

hits = pd.concat([res[k][res[k]["uic"] == uic].assign(check=checks.BY_KEY[k].title + f" ({checks.BY_KEY[k].kind})")
                  for k in res], ignore_index=True)
st.subheader("Check results")
if hits.empty:
    st.success("No check results for this well.")
else:
    st.dataframe(hits[["check", "finding", "detail", "since"]], hide_index=True, width="stretch",
                 column_config={"since": st.column_config.DateColumn("Since", format="YYYY-MM-DD")})

st.subheader("H-10 monthly injection")
m = data.well_months(uic)
if m.empty:
    st.write("No H-10 monthly data on file.")
else:
    yrs = st.slider("Years shown", 1, max(1, int(m["month"].dt.year.nunique())), min(10, m["month"].dt.year.nunique()))
    m = m[m["month"] >= m["month"].max() - pd.DateOffset(years=yrs)]
    p = m.set_index("month")[["max_psi", "avg_psi"]].rename(columns={"max_psi": "Max psig", "avg_psi": "Avg psig"})
    if r["max_psi"]:
        p["Permit max psig"] = int(r["max_psi"])
    st.line_chart(p, height=260)
    v = m.set_index("month")
    if v["bbl"].sum():
        vv = (v["bbl"] / v.index.days_in_month).rename("Avg bbl/day").to_frame()
        if r["max_bbl_day"]:
            vv["Permit max bbl/day"] = int(r["max_bbl_day"])
        st.line_chart(vv, height=220)
    if v["mcf"].sum():
        vm = (v["mcf"] / v.index.days_in_month).rename("Avg Mcf/day").to_frame()
        if r["max_mcf_day"]:
            vm["Permit max Mcf/day"] = int(r["max_mcf_day"])
        st.line_chart(vm, height=220)
    with st.expander("Monthly rows"):
        st.dataframe(m[["month", "avg_psi", "max_psi", "bbl", "mcf"]].sort_values("month", ascending=False),
                     hide_index=True, column_config={"month": st.column_config.DateColumn("Month", format="YYYY-MM")})

st.subheader("Pressure tests (H-5)")
h = t["h5"][t["h5"]["uic"] == uic].copy()
if h.empty:
    st.write("None on file.")
else:
    h["result"] = h["result"].map(lambda c: codes.H5_RESULT.get(c, c))
    h["schedule_type"] = h["schedule_type"].map(lambda c: codes.H5_SCHEDULE_TYPE.get(c, c))
    h["test_type"] = h["test_type"] + h["alt_test"].map(lambda c: f" ({codes.H5_ALT_TEST[c]})"
                                                        if c in codes.H5_ALT_TEST else "")
    st.dataframe(h.drop(columns=["uic", "alt_test"]).sort_values("due", ascending=False), hide_index=True,
                 width="stretch")

st.subheader("H-10 violations")
v = t["h10_violations"][t["h10_violations"]["uic"] == uic].copy()
if v.empty:
    st.write("None on file.")
else:
    v["code"] = v["code"].map(lambda c: codes.label(codes.H10_VIOLATION, c))
    v["resolved_by"] = v["resolved_by"].map(lambda c: codes.H10_RESOLVED_BY.get(c, c))
    st.dataframe(v.drop(columns=["uic"]).sort_values("cycle_start", ascending=False), hide_index=True,
                 width="stretch")

st.subheader("Enforcement actions")
e = t["enforcement"][t["enforcement"]["uic"] == uic].copy()
if e.empty:
    st.write("None on file.")
else:
    e["violation"] = e["violation"].map(lambda c: codes.label(codes.ENF_VIOLATION, c))
    e["notice"] = e["notice"].map(lambda c: codes.label(codes.ENF_NOTICE, c))
    e["compliance_method"] = e["compliance_method"].map(lambda c: codes.label(codes.ENF_COMPLIANCE, c))
    st.dataframe(e.drop(columns=["uic"]), hide_index=True, width="stretch")
    er = t["enforcement_remarks"][t["enforcement_remarks"]["uic"] == uic]
    if not er.empty:
        st.caption("Enforcement remarks: " + " | ".join(er["text"]))

with st.expander("Permit remarks"):
    rm = data.well_remarks(uic)
    st.dataframe(rm.drop(columns=["uic"], errors="ignore"), hide_index=True, width="stretch")
