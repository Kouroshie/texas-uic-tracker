import pandas as pd
import streamlit as st

from uicpublic import checks, data, ui
from uicpublic.help import TIP, coverage, page_help
from uicpublic.checks import in_service

t = ui.get_tables()
res = ui.get_checks()
w = t["wells"]
svc = w[in_service(w)]

st.title("Texas UIC Tracker")
st.write("Injection, disposal and storage wells permitted by the Railroad Commission of Texas, from the RRC's public "
         "UIC database, with checks that point to wells worth a closer look.")
page_help("overview")

c = st.columns(4)
c[0].metric("Wells in the database", f"{len(w):,}", help=TIP["wells_total"])
c[1].metric("Permits in service", f"{len(svc):,}", help=TIP["in_service"])
c[2].metric("Reported active on latest H-10", f"{int(svc['h10_status'].eq('3').sum()):,}", help=TIP["active"])
c[3].metric("Wells with any check result", f"{pd.concat([r['uic'] for r in res.values()]).nunique():,}",
             help=TIP["with_results"])

st.subheader("Check results", help=TIP["check_table"])
rows = [{"Check": c.title, "Kind": c.kind, "Wells": int(res[c.key]["uic"].nunique()),
         "Operators": int(res[c.key]["operator_no"].nunique()), "What it means": c.explain} for c in checks.CHECKS]
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={"What it means": st.column_config.TextColumn(width="large"),
                            "Kind": st.column_config.TextColumn(help=TIP["kind"])})
st.caption("RRC record = recorded by the RRC in its own database. Screen = computed here from reported and "
           "permitted numbers; a prompt to look closer, not a violation.")

st.subheader("Permits in service by district", help=TIP["district_chart"])
by = svc.groupby("district").agg(wells=("uic", "size"),
                                 active=("h10_status", lambda s: int(s.eq("3").sum()))).reset_index()
flagged = pd.concat([r[["uic"]] for r in res.values()]).drop_duplicates()
by = by.merge(svc[svc["uic"].isin(flagged["uic"])].groupby("district").size().rename("with_results").reset_index(),
              on="district", how="left").fillna({"with_results": 0})
by = by[by["district"] != ""]
st.bar_chart(by.set_index("district")[["active", "with_results"]], stack=False, height=320)
st.dataframe(by.rename(columns={"district": "District", "wells": "Permits in service", "active": "Reported active",
                                "with_results": "With a check result"}), hide_index=True)

st.subheader("What years the data covers", help="First and last year with real records in each data set. A few "
             "typing-error dates in the RRC file (for example 1900 or 2098) are ignored.")
st.dataframe(coverage(st.session_state["stamp"]), hide_index=True, width="stretch",
             column_config={"What": st.column_config.TextColumn(width="large")})
