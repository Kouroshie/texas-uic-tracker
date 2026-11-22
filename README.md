# Texas UIC Tracker

An open-source web app for looking up Texas injection, disposal and storage wells and screening them for possible
compliance problems, built only from public data.

> **Unofficial.** Not affiliated with or endorsed by the Railroad Commission of Texas (RRC). Results marked
> *Screen* are prompts to look closer, not findings of a violation. Check the RRC's own records before acting.

## What it does

- **Overview**: wells in the RRC's UIC database, permits in service, and how many wells each check flags, by district.
- **Screening checks**: twelve checks in two kinds.
  - *RRC record*: open enforcement actions, unresolved H-10 violations, H-10 reports not received after a second
    notice, overdue H-5 pressure tests, and a latest pressure test that failed.
  - *Screen*: reported pressure above the permitted maximum, average daily volume above the permitted maximum, no
    passing pressure test in 5 years, no recent H-10 data, injection with no completion report, injection after
    cancel or plugging, and gaps in TexNet daily reporting.
- **Well record**: permit limits, H-10 monthly pressure and volume charts against the permit, H-5 tests, H-10
  violations, enforcement actions and permit remarks for any UIC, API or lease number.
- **Operators**: permits and check results per operator.
- Every list downloads as CSV or Excel.

## Data

| Source | Used for |
|---|---|
| RRC [UIC Database](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/) (ASCII, monthly) | permits, limits, H-10 monthly reports, H-5 tests, enforcement, H-10 violations, remarks |
| RRC P-5 Organization file (monthly) | operator names |
| [TexNet](https://injection.texnet.beg.utexas.edu/) injection wells (Bureau of Economic Geology, public ArcGIS service) | daily injection reporting dates |

No logins or keys. The record layouts follow the RRC's UIC database manual (UIA010). Permit special conditions
are not in the public file, so they are not checked.

A GitHub workflow (`.github/workflows/data.yml`) rebuilds the data on the 6th of every month and publishes it as
the `data` release. The app downloads that release on first start.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

To build the data yourself instead of downloading it (about 5 minutes and 300 MB of downloads):

```bash
python build_data.py
```

Tests: `python -m pytest`

## Deploy

On [Streamlit Community Cloud](https://share.streamlit.io): New app, pick this repository, main file `app.py`.

## License

MIT. Data is public information from the Railroad Commission of Texas and the Bureau of Economic Geology.
