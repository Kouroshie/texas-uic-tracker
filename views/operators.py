import pandas as pd
import streamlit as st

from uicpublic import checks, ui
from uicpublic.help import TIP, page_help
from uicpublic.checks import in_service

t = ui.get_tables()
res = ui.get_checks()
w = t["wells"]
svc = w[in_service(w)]

st.title("Operators", help=TIP["operators_table"])
st.write("Permits in service and check results per operator. Pick an operator to see its wells.")
page_help("operators")

base = svc.groupby(["operator_no", "operator"], as_index=False).agg(
    permits=("uic", "size"), active=("h10_status", lambda s: int(s.eq("3").sum())))
for c in checks.CHECKS:
    n = res[c.key].groupby("operator_no")["uic"].nunique().rename(c.title)
    base = base.merge(n, left_on="operator_no", right_index=True, how="left")
titles = [c.title for c in checks.CHECKS]
base[titles] = base[titles].fillna(0).astype(int)
flag = pd.concat([res[c.key][["operator_no", "uic"]] for c in checks.CHECKS if c.kind == "RRC record"])
base = base.merge(flag.groupby("operator_no")["uic"].nunique().rename("Wells with an RRC-record result"),
                  left_on="operator_no", right_index=True, how="left")
base["Wells with an RRC-record result"] = base["Wells with an RRC-record result"].fillna(0).astype(int)
base = base.sort_values(["permits"], ascending=False)

name = st.text_input("Operator name or number contains", help=TIP["operator_text"]).strip().upper()
view = base if not name else base[base["operator"].str.upper().str.contains(name, regex=False)
                                  | base["operator_no"].str.contains(name, regex=False)]
ev = st.dataframe(view.rename(columns={"operator_no": "Operator no.", "operator": "Operator",
                                       "permits": "Permits in service", "active": "Reported active"}),
                  hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                  column_config={"Permits in service": st.column_config.NumberColumn(help=TIP["in_service"]),
                                 "Reported active": st.column_config.NumberColumn(help=TIP["active"]),
                                 "Wells with an RRC-record result": st.column_config.NumberColumn(help=TIP["rrc_record_col"]),
                                 **{c.title: st.column_config.NumberColumn(help=c.explain) for c in checks.CHECKS}})
ui.downloads(view, "uic_operators")

rows = ev.selection.rows if ev and ev.selection else []
if rows:
    op = view.iloc[rows[0]]
    st.subheader(f"{op['operator']} ({op['operator_no']})")
    hits = pd.concat(res.values(), ignore_index=True)
    hits = hits[hits["operator_no"] == op["operator_no"]]
    hits["check"] = hits["check"].map(lambda k: f"{checks.BY_KEY[k].title} ({checks.BY_KEY[k].kind})")
    ui.well_table(hits[["uic", "check", "lease", "well_no", "county", "finding", "detail", "since"]], "op_hits")
    ui.downloads(hits, f"uic_operator_{op['operator_no']}")
