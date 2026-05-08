# Flight Delay Analysis Project

This project provides a command-line interface and a Streamlit-based tuning tool for querying flight delay data from a SQLite database and creating FAA-style visualizations.

## Overview

The project contains two main user-facing entry points:

- `main.py` runs the command-line application for database queries and chart generation.
- `guide_tuner_app.py` runs a Streamlit app for interactively tuning chart layout and branding tokens.

The visualization system is controlled by `visualization_guide.json`, while the actual chart rendering logic lives in `visualizations.py`.

## Features

- Query a flight by database ID
- Query flights by date
- Query delayed flights by airline
- Query delayed flights by origin airport
- Export query results to CSV with automatically generated, descriptive filenames
- Render a branded chart showing delayed departure share by airline
- Tune chart layout, logo size, title positions, margins, and tick rotation through Streamlit

## Project Structure

```text
project/
├── main.py
├── flights_data.py
├── visualizations.py
├── guide_tuner_app.py
├── visualization_guide.json
├── README.md
├── requirements.txt
├── data/
│   └── flights_v2.sqlite3
├── media/
│   └── FAALogo.jpeg
└── results/
```

## Installation

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the CLI

Start the command-line application:

```bash
python main.py
```

The main menu looks like this:

```text
Menu:
1. Show flight by ID
2. Show flights by date
3. Delayed flights by airline (full name / airline IATA code / alias)
4. Delayed flights by origin (airport IATA code / city / state)
5. Create visualizations
6. Exit
```

## Running the Streamlit Tuner

Start the tuning app with Streamlit:

```bash
streamlit run guide_tuner_app.py
```

Do not start the tuner with plain `python guide_tuner_app.py`, because the intended runtime is Streamlit.

## Database

The project uses a SQLite database located at:

```text
data/flights_v2.sqlite3
```

### Database tables

The database contains three core tables.

#### 1. `airlines`

```sql
CREATE TABLE "airlines" (
    "ID" INTEGER,
    "AIRLINE" TEXT UNIQUE,
    "IATA_CODE" INTEGER UNIQUE,
    "ALIAS" INTEGER UNIQUE,
    PRIMARY KEY("ID")
)
```

Purpose:
- Stores airline master data
- Links to `flights.AIRLINE` via `airlines.ID`

Important columns:
- `ID`: internal airline identifier
- `AIRLINE`: airline name
- `IATA_CODE`: airline code
- `ALIAS`: optional alternate airline identifier

#### 2. `airports`

```sql
CREATE TABLE "airports" (
    "IATA_CODE" TEXT,
    "AIRPORT" TEXT,
    "CITY" TEXT,
    "STATE" TEXT,
    "COUNTRY" TEXT,
    "LATITUDE" TEXT,
    "LONGITUDE" TEXT,
    PRIMARY KEY("IATA_CODE")
)
```

Purpose:
- Stores airport reference data
- Supports airport lookup by IATA code, city, and state

Important columns:
- `IATA_CODE`: airport identifier
- `AIRPORT`: airport name
- `CITY`: city name
- `STATE`: state or region
- `COUNTRY`: country
- `LATITUDE`: latitude as text
- `LONGITUDE`: longitude as text

#### 3. `flights`

```sql
CREATE TABLE "flights" (
    "ID" INTEGER,
    "YEAR" TEXT,
    "MONTH" TEXT,
    "DAY" NUMERIC,
    "DAY_OF_WEEK" TEXT,
    "AIRLINE" INTEGER,
    "FLIGHT_NUMBER" INTEGER,
    "TAIL_NUMBER" INTEGER,
    "ORIGIN_AIRPORT" TEXT,
    "DESTINATION_AIRPORT" TEXT,
    "SCHEDULED_DEPARTURE" TEXT,
    "DEPARTURE_TIME" TEXT,
    "DEPARTURE_DELAY" INTEGER,
    "TAXI_OUT" TEXT,
    "WHEELS_OFF" TEXT,
    "SCHEDULED_TIME" TEXT,
    "ELAPSED_TIME" TEXT,
    "AIR_TIME" INTEGER,
    "DISTANCE" INTEGER,
    "WHEELS_ON" INTEGER,
    "TAXI_IN" INTEGER,
    "SCHEDULED_ARRIVAL" TEXT,
    "ARRIVAL_TIME" INTEGER,
    "ARRIVAL_DELAY" INTEGER,
    "DIVERTED" TEXT,
    "CANCELLED" INTEGER,
    "CANCELLATION_REASON" INTEGER,
    "AIR_SYSTEM_DELAY" INTEGER,
    "SECURITY_DELAY" INTEGER,
    "AIRLINE_DELAY" INTEGER,
    "LATE_AIRCRAFT_DELAY" INTEGER,
    "WEATHER_DELAY" INTEGER,
    PRIMARY KEY("ID" AUTOINCREMENT)
)
```

Purpose:
- Stores the operational flight records
- Provides the source data for CLI searches and visualizations

Important columns:
- `ID`: unique flight record ID
- `YEAR`, `MONTH`, `DAY`: date components used by CLI filters
- `AIRLINE`: foreign key-like reference to `airlines.ID`
- `ORIGIN_AIRPORT`: origin airport IATA code
- `DESTINATION_AIRPORT`: destination airport IATA code
- `DEPARTURE_DELAY`: departure delay in minutes
- `ARRIVAL_DELAY`: arrival delay in minutes
- `DISTANCE`: route distance
- `CANCELLED`: cancellation flag

## Delay logic

This project uses `DEPARTURE_DELAY` as the single delay field for:
- CLI result display
- delayed-flight filtering
- airline delay visualization

A flight is treated as delayed when:

- `DEPARTURE_DELAY >= 20`

## Export behavior

After each query, the CLI offers to export the displayed results to CSV:

```text
Got N results.
Would you like to export this data to a CSV file? (y/n)
```

If the user confirms, the filename is generated automatically based on:
- query type (flight, date, airline, origin)
- input value
- number of results

Examples:

- Flight by ID:
  - Input: `2`
  - CSV: `flight_ID2_1.csv`

- Flights by date:
  - Input: `08/05/2016` or `08052016`
  - CSV: `flights_20160508_143.csv`

- Delayed flights by airline:
  - Input: `AA`
  - CSV: `flights_AA_delayed_departure_38.csv`

- Delayed flights by origin:
  - Input: `JFK`
  - CSV: `flights_JFK_delayed_22.csv`

All CSV files are written to:

```text
results/
```

The filename is created automatically; the user does not need to type it.

## Date input

For menu item “Show flights by date”, the CLI accepts:

- `DD/MM/YYYY` (e.g. `08/05/2016`)
- 8 digits without separators (e.g. `08052016`)

If 8 digits are entered, the CLI automatically inserts slashes and interprets the value as `DD/MM/YYYY` before parsing.

## Visualization system

### `visualizations.py`

This module:
- reads data from `data/flights_v2.sqlite3`
- calculates the share of delayed departures by airline
- creates a branded Matplotlib chart
- places a logo in the header instead of a text headline
- applies layout values from `visualization_guide.json`

### `visualization_guide.json`

This file stores:
- branding settings
- palette settings
- typography settings
- layout settings
- chart defaults
- tuned values saved from the Streamlit tuner

### `guide_tuner_app.py`

This app:
- previews the active chart
- allows layout tuning in the sidebar
- lets the user resize and reposition the logo
- saves updated values back into `_tuned_token_values`

## Notes on code quality

The updated code follows these principles:

- Magic numbers were reduced by extracting repeated values into named constants.
- Functions and major sections are documented in English.
- Streamlit `use_container_width` was replaced with the current `width="stretch"` API.
- Complex values shown in Streamlit tables are serialized to strings to avoid Arrow warnings.
- The logic now consistently uses `DEPARTURE_DELAY` instead of a generic `DELAY` alias.
- CSV filenames are generated automatically and reflect the query structure.

## Expected companion module

The CLI depends on `flights_data.py`. That module provides at least these functions:

- `get_flight_by_id(flight_id)`
- `get_flights_by_date(day, month, year)`
- `get_delayed_flights_by_airline(airline_input)`
- `get_delayed_flights_by_airport(iata_code)`
- `search_airports(term)`

Those query functions return rows that include at least:

- `ID`
- `AIRLINE`
- `ORIGIN_AIRPORT`
- `DESTINATION_AIRPORT`
- `DEPARTURE_DELAY`

## Output

Generated files are written to:

```text
results/
```

This includes:
- exported CSV files
- rendered chart images

## Troubleshooting

### Streamlit warning about `width`

Older versions of the project used `use_container_width=True`. The current code uses the modern API:

- `width="stretch"`

to avoid deprecation warnings.

### Arrow serialization warning in Streamlit

A previous Arrow warning was caused by lists and dictionaries inside a DataFrame column in the tuner UI. The fix is to serialize complex token values to strings before calling `st.dataframe(...)`.

### ScriptRunContext warning

If Streamlit prints a `missing ScriptRunContext` warning, start the app with:

```bash
streamlit run guide_tuner_app.py
```

instead of plain Python execution.