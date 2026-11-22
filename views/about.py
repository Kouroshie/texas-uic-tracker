import streamlit as st

from uicpublic import checks, data

m = data.meta()
st.title("About and methods")
st.markdown(f"""
**Texas UIC Tracker** is an unofficial, open-source tool. It is not affiliated with or endorsed by the Railroad
Commission of Texas (RRC). It uses only public data and needs no login.

### Data sources
| Source | What it gives | Copy used |
|---|---|---|
| RRC [UIC Database](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/) (ASCII, monthly) | Permits, permitted limits, H-10 annual monitoring reports by month, H-5 pressure tests, enforcement actions, H-10 violations, remarks | listed {m['uic_database_listed']} |
| RRC P-5 Organization file (monthly) | Operator names and P-5 status | listed {m['p5_listed']} |
| [TexNet injection data](https://injection.texnet.beg.utexas.edu/), Bureau of Economic Geology | First and last day of daily injection reporting | {m['texnet']} |

The data is rebuilt every month by a GitHub workflow and published with the source code. Record layouts follow the
RRC's UIC database manual (UIA010). Built {m['built']}.

### Two kinds of check result
- **RRC record**: something the RRC recorded in its own database, such as an enforcement action with no compliance
  date or an H-10 violation with no resolved date.
- **Screen**: something this tool computes by comparing reported numbers with permit numbers. Treat it as a question,
  not a finding. Typing errors in reports, amended permits, multi-zone permits and permit terms that are not in the
  public file all produce false hits.

Public data lags: H-10 reports are annual, and the database file is a monthly snapshot. Permit special conditions
are not in the public file, so this tool cannot check them.

### Checks
""")
for c in checks.CHECKS:
    st.markdown(f"- **{c.title}** ({c.kind}): {c.explain}")
st.markdown("""
### Verify before acting
Confirm anything here against the RRC's own systems: the
[Injection-Storage Permit Query](https://webapps2.rrc.texas.gov/EWA/uicQueryAction.do), the
[H-10 Filing Query](https://webapps.rrc.texas.gov/H10/searchH10.do) and the RRC's imaged records.

Source code and issues: [github.com/Kouroshie/texas-uic-tracker](https://github.com/Kouroshie/texas-uic-tracker).
MIT license.
""")
