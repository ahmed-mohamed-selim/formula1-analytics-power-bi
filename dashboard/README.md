# Power BI dashboard

`F1_Dashboard.pbix` is a six-page, interactive report built on the star schema produced by the Python pipeline (14 tables, 23 relationships, 24 DAX measures in the `_Measures` table).

| Page | Focus |
| --- | --- |
| Overview | Season pulse: races, wins, finish and retirement rates |
| Drivers | Wins, podiums, poles and win rate by driver |
| Constructors | Team wins, titles and points |
| Circuits | Most-hosted circuits, countries and reliability by track |
| Race Performance | Grid vs finish, positions gained, pit stops, fastest laps |
| Reliability | Retirement causes and finish rates |

## Features

- Navigation menu on every page, with hover states.
- Slicers synced across pages (driver, team, season window).
- Custom theme (`assets/F1RossoGraphite.json`) and generated page backgrounds (`assets/backgrounds`).

## Open it

1. Open `F1_Dashboard.pbix` in Power BI Desktop (December 2025 release or newer recommended).
2. The model is embedded, so no refresh is needed. To rebuild the data, run the pipeline (see the main README), then point the queries at `data/warehouse/csv`.
3. Format the rate measures (`Win Rate`, `Podium Rate`, `Retirement Rate`, `Finish Rate`, `Pole Conversion`) as Percentage if they show as decimals.

## Credits

The car render used on the page backgrounds was produced from a third-party 3D model. The model files are not included in this repository.
