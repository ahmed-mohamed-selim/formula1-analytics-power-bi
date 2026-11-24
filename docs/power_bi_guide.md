# Power BI Guide

## 1. Load the data

1. Run `f1-analytics build --source <archive.zip>`.
2. In Power BI Desktop choose **Get data > Parquet** and load every file in `data/warehouse/parquet`, or **Get data > Text/CSV** for `data/warehouse/csv`.
3. Keep the table names exactly as the file names (for example `fact_results`).

## 2. Create the relationships

All relationships are one-to-many from the dimension to the fact, single direction, and active.

| From (one) | To (many) |
| --- | --- |
| `dim_date[date_key]` | `dim_race[date_key]` |
| `dim_circuit[circuit_id]` | `dim_race[circuit_id]` |
| `dim_race[race_id]` | `race_id` in every fact table |
| `dim_driver[driver_id]` | `driver_id` in `fact_results`, `fact_sprint_results`, `fact_race_performance`, `fact_pit_stops`, `fact_lap_times`, `fact_practice_sessions`, `fact_driver_standings` |
| `dim_constructor[constructor_id]` | `constructor_id` in `fact_results`, `fact_sprint_results`, `fact_practice_sessions`, `fact_constructor_standings` |
| `dim_status[status_id]` | `status_id` in `fact_results`, `fact_sprint_results` |

## 3. Model settings

- Mark `dim_date` as the date table using `date`.
- Sort `dim_date[month_name]` by `month` and `dim_date[day_name]` by `day_of_week`.
- Sort `dim_race[era]` by `dim_race[decade]`.
- Hide all key columns (`*_id`, `date_key`) and set numeric columns that should not be aggregated (`year`, `round`, `decade`) to **Don't summarize**.
- Format `*_ms` columns as whole numbers and `duration_s` with three decimals.

## 4. Avoid common modelling errors

| Risk | Guidance |
| --- | --- |
| Many-to-many between facts | Never relate two fact tables directly. `fact_race_performance` and `fact_results` meet only through `dim_race` and `dim_driver` |
| Duplicate `(race_id, driver_id)` pairs | They exist only in `fact_results` for 1950-1964 shared drives. Use `result_id` as the row key and do not relate on the pair |
| Summing standings | `fact_driver_standings` and `fact_constructor_standings` hold cumulative values after every round. Filter on `is_season_final` before summing |
| Blank means no coverage | Qualifying, lap, pit stop and sprint data start in different seasons. Use `dim_race[has_qualifying_data]`, `[has_lap_data]` and `[has_pit_data]` as page or visual filters |
| Averaging outliers | Keep `is_outlier_lap` and `is_outlier_stop` set to false in visuals that average times |
| Booleans in CSV | If you load CSV, confirm the `is_*` columns are typed as True/False |

## 5. DAX measures

Create a table named `_Measures` and add the following.

```dax
Races = DISTINCTCOUNT ( fact_results[race_id] )

Starts =
CALCULATE ( COUNTROWS ( fact_results ), fact_results[is_dns] = FALSE () )

Wins =
CALCULATE ( COUNTROWS ( fact_results ), fact_results[is_win] = TRUE () )

Podiums =
CALCULATE ( COUNTROWS ( fact_results ), fact_results[is_podium] = TRUE () )

Poles =
CALCULATE ( COUNTROWS ( fact_results ), fact_results[started_on_pole] = TRUE () )

Fastest Laps =
CALCULATE ( COUNTROWS ( fact_results ), fact_results[has_fastest_lap] = TRUE () )

Retirements =
CALCULATE ( COUNTROWS ( fact_results ), fact_results[is_dnf] = TRUE () )

Win Rate = DIVIDE ( [Wins], [Starts] )

Podium Rate = DIVIDE ( [Podiums], [Starts] )

Retirement Rate = DIVIDE ( [Retirements], [Starts] )

Finish Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_results ), fact_results[is_finished] = TRUE () ),
    [Starts]
)

Pole Conversion =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_results ),
        fact_results[started_on_pole] = TRUE (),
        fact_results[is_win] = TRUE ()
    ),
    [Poles]
)

Race Points = SUM ( fact_results[points] )

Sprint Points = SUM ( fact_sprint_results[points] )

Total Points = [Race Points] + [Sprint Points]

Avg Grid Position = AVERAGE ( fact_results[grid_position] )

Avg Finish Position = AVERAGE ( fact_results[finish_position] )

Avg Positions Gained = AVERAGE ( fact_results[positions_gained] )

Season Points =
CALCULATE (
    SUM ( fact_driver_standings[points] ),
    fact_driver_standings[is_season_final] = TRUE ()
)

Driver Titles =
CALCULATE (
    COUNTROWS ( fact_driver_standings ),
    fact_driver_standings[is_season_final] = TRUE (),
    fact_driver_standings[position] = 1
)

Constructor Titles =
CALCULATE (
    COUNTROWS ( fact_constructor_standings ),
    fact_constructor_standings[is_season_final] = TRUE (),
    fact_constructor_standings[position] = 1
)

Avg Pit Stop (s) =
CALCULATE (
    AVERAGE ( fact_pit_stops[duration_s] ),
    fact_pit_stops[is_outlier_stop] = FALSE ()
)

Avg Stops per Driver =
AVERAGE ( fact_race_performance[pit_stops] )

Best Lap (s) =
DIVIDE (
    CALCULATE ( MIN ( fact_lap_times[lap_time_ms] ), fact_lap_times[is_outlier_lap] = FALSE () ),
    1000
)
```

`Season Points`, `Driver Titles` and `Constructor Titles` are meaningful at season or driver level. Use them with `dim_race[year]` or `dim_driver[driver_name]` in the filter context.

## 6. Dashboard design

| Page | Purpose | Visuals |
| --- | --- | --- |
| Overview | Entry point | Cards for `Races`, `Wins`, `Podiums`, `Poles`; line chart of `Finish Rate` by `year`; table of season champions using `Driver Titles` |
| Drivers | Compare drivers | Slicers for `dim_race[era]` and `dim_driver[nationality]`; bar chart of `Wins` by driver; scatter of `Win Rate` against `Starts`; matrix of `Podiums` by year |
| Constructors | Team performance | Stacked column of `Wins` by `decade` and constructor; line chart of `Season Points`; `Retirement Rate` by constructor |
| Circuits | Track insights | Map of `dim_circuit` with `Retirement Rate` as bubble size; bar chart of `Pole Conversion` by circuit; `Avg Positions Gained` table |
| Qualifying and grid | Starting position impact | Column chart of `Win Rate` by `grid_position`; heat map of `Podium Rate` by grid position and era |
| Race strategy | Pit stops and pace | Line chart of `Avg Pit Stop (s)` by year; `Avg Stops per Driver` by year; `Best Lap (s)` by circuit. Filter on `dim_race[has_pit_data]` |

Use a consistent theme: neutral background, one accent colour (`#E10600`), and the same era ordering on every page.
