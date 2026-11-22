# Texas UIC Tracker

An open-source web app for looking up Texas injection, disposal and storage wells and screening them for possible
compliance problems, built only from public data.

**Open the app:** https://kouroshie-texas-uic-tracker-app-1zchb4.streamlit.app

> **Unofficial.** Not affiliated with or endorsed by the Railroad Commission of Texas (RRC). Results marked
> *Screen* are prompts to look closer, not findings of a violation. Check the RRC's own records before acting.

## What it does

- **Overview**: wells in the RRC's UIC database, permits in service, and how many wells each check flags, by district.
- **Screening checks**: eleven checks in two kinds.
  - *RRC record*: enforcement actions in the RRC's file with no compliance date.
  - *Screen*: H-10 violations still open in the file (last 3 reporting years), H-5 pressure tests past due, a
    latest pressure test that failed, reported pressure more than 100 psig above the permitted maximum, average daily
    volume above the permitted maximum, no passing pressure test in 5 years, no recent H-10 data, injection with no
    completion report, injection after cancel or plugging, and gaps in TexNet daily reporting.
  - Checks run as of the date the RRC lists for its monthly file, not today's date.
- **Well record**: permit limits, H-10 monthly pressure and volume charts against the permit, H-5 tests, H-10
  violations and enforcement actions for any UIC, API or lease number.
- **Operators**: permits and check results per operator.
- Every list downloads as CSV or Excel.

## Data

| Source | Used for | Record layout |
|---|---|---|
| RRC [UIC Database](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/#underground-injection-control-database) (ASCII, monthly) | permits, limits, H-10 monthly reports, H-5 tests, enforcement, H-10 violations | [Manual UIA010 (PDF)](https://www.rrc.texas.gov/media/v3onmigl/uic_manual_uia010_3116.pdf) |
| RRC [P-5 Organization](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/#p5-organization) file (monthly) | operator names | [Manual ORA001 (PDF)](https://www.rrc.texas.gov/media/jtqfynn3/ora001_p5_manual_october-2014.pdf) |
| [TexNet](https://injection.texnet.beg.utexas.edu/) injection wells (Bureau of Economic Geology) | daily injection reporting dates | [Public map service, wells layer](https://maps.texnet.beg.utexas.edu/arcgis/rest/services/injection/Injection/MapServer/0) |

No logins or keys. Permit special conditions
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

## License

MIT. Data is public information from the Railroad Commission of Texas and the Bureau of Economic Geology.
