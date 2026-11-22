import streamlit as st

from uicpublic import checks, data, ui
from uicpublic.help import check_window, coverage, page_help

m = data.meta()
st.title("About and methods")
page_help("about")
st.markdown(f"""
**Texas UIC Tracker** is an unofficial, open-source tool. It is not affiliated with or endorsed by the Railroad
Commission of Texas (RRC). It uses only public data and needs no login.

### Data sources
| Source | What it gives | Record layout | Copy used |
|---|---|---|---|
| RRC [UIC Database](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/#underground-injection-control-database) (ASCII, monthly) | Permits, permitted limits, H-10 annual monitoring reports by month, H-5 pressure tests, enforcement actions, H-10 violations | [Manual UIA010 (PDF)](https://www.rrc.texas.gov/media/v3onmigl/uic_manual_uia010_3116.pdf) | listed {m['uic_database_listed']} |
| RRC [P-5 Organization](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/#p5-organization) file (monthly) | Operator names and P-5 status | [Manual ORA001 (PDF)](https://www.rrc.texas.gov/media/jtqfynn3/ora001_p5_manual_october-2014.pdf) | listed {m['p5_listed']} |
| [TexNet injection data](https://injection.texnet.beg.utexas.edu/), Bureau of Economic Geology | First and last day of daily injection reporting | [Public map service, wells layer](https://maps.texnet.beg.utexas.edu/arcgis/rest/services/injection/Injection/MapServer/0) | {m['texnet']} |

The data is rebuilt every month by a GitHub workflow and published with the source code. Record layouts follow the
manuals linked above. Built {m['built']}.

""")
st.markdown("### What years the data covers", help="First and last year with real records in each data set. A few typing-error dates in the RRC file (for example 1900 or 2098) are ignored.")
st.dataframe(coverage(st.session_state["stamp"]), hide_index=True, width="stretch",
             column_config={"What": st.column_config.TextColumn(width="large")})
st.markdown(f"""
### Two kinds of check result
- **RRC record**: something the RRC recorded in its own database file, such as an enforcement action with no
  compliance date.
- **Screen**: something this tool computes by comparing reported numbers with permit numbers. Treat it as a question,
  not a finding. Typing errors in reports, amended permits, multi-zone permits and permit terms that are not in the
  public file all produce false hits.

Public data lags: H-10 reports are annual, and the database file is a monthly snapshot, so checks run as of the date
the RRC lists for that file ({m.get('checks_as_of', 'the file date')}). The RRC's online queries are the current record;
for example, some H-10 violations still open in the file are shown resolved online. Permit special conditions
are not in the public file, so this tool cannot check them. The RRC's free-text remarks are left out because
they include people's phone numbers and email addresses.

### Checks
""")
as_of = data.snapshot_date(m)
for c in checks.CHECKS:
    st.markdown(f"- **{c.title}** ({c.kind}): {c.explain} *Dates looked at: {check_window(c.key, ui.get_tables(), as_of)}*")
st.markdown("""
### Verify before acting
Confirm anything here against the RRC's own systems: the
[Injection-Storage Permit Query](https://webapps2.rrc.texas.gov/EWA/uicQueryAction.do), the
[H-10 Filing Query](https://webapps.rrc.texas.gov/H10/searchH10.do) and the RRC's imaged records.

Source code and issues: [github.com/Kouroshie/texas-uic-tracker](https://github.com/Kouroshie/texas-uic-tracker).
MIT license.
""")
