"""Texas UIC Tracker: an unofficial, open-source view of the Railroad Commission of Texas' public injection and
disposal well data, with screening checks. Run with:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from uicpublic import data

st.set_page_config(page_title="Texas UIC Tracker", page_icon=":material/oil_barrel:", layout="wide")

DISCLAIMER = ("Unofficial tool. Not affiliated with or endorsed by the Railroad Commission of Texas (RRC). "
              "Built only from public data. Screening results are prompts to look closer, not findings of a "
              "violation. Check the RRC's own records before relying on anything here.")


def ensure_data() -> str:
    if not data.have_data():
        with st.spinner("First start: downloading the prebuilt public data (about 100 MB)..."):
            try:
                data.download()
            except Exception as e:
                st.error(f"Could not download the data ({e}). Build it locally with `python build_data.py`.")
                st.stop()
    refresh_if_stale()
    return data.meta()["built"]


@st.cache_resource(ttl=86400, show_spinner=False)
def refresh_if_stale() -> None:
    """At most once a day: a long-running server picks up the monthly rebuild."""
    if data.stale(data.meta()):
        try:
            data.download()
        except Exception:
            pass  # keep the copy we have


stamp = ensure_data()
st.session_state["stamp"] = stamp

nav = st.navigation([
    st.Page("views/overview.py", title="Overview", icon=":material/dashboard:", default=True),
    st.Page("views/checks_page.py", title="Screening checks", icon=":material/checklist:"),
    st.Page("views/well.py", title="Well record", icon=":material/search:"),
    st.Page("views/operators.py", title="Operators", icon=":material/factory:"),
    st.Page("views/about.py", title="About and methods", icon=":material/info:"),
])
m = data.meta()
st.sidebar.caption(f"RRC UIC database: copy listed {m['uic_database_listed']}  \n"
                   f"Latest H-10 month: {str(m['latest_h10_month'])[:4]}-{str(m['latest_h10_month'])[4:]}  \n"
                   f"TexNet: {m['texnet']}  \nChecks as of {m.get('checks_as_of', 'today')}  \n"
                   f"Built {m['built']}")
st.sidebar.caption(DISCLAIMER)
nav.run()
