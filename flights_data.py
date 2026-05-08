"""
Database access layer for the flight delay analysis project.

This module contains all SQL queries used by the CLI. The implementation is
aligned with the real flights_v2.sqlite3 schema and consistently uses the
DEPARTURE_DELAY column from the flights table.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text

DATABASE_URL = "sqlite:///data/flights_v2.sqlite3"
engine = create_engine(DATABASE_URL)

DELAY_THRESHOLD_MINUTES = 20
IATA_CODE_LENGTH = 3

BASE_RESULT_COLUMNS = """
    f.ID,
    a.AIRLINE,
    f.ORIGIN_AIRPORT,
    f.DESTINATION_AIRPORT,
    f.DEPARTURE_DELAY
"""

QUERY_FLIGHT_BY_ID = f"""
SELECT
    {BASE_RESULT_COLUMNS}
FROM flights f
JOIN airlines a
    ON f.AIRLINE = a.ID
WHERE f.ID = :id
ORDER BY f.ID
"""

QUERY_FLIGHTS_BY_DATE = f"""
SELECT
    {BASE_RESULT_COLUMNS}
FROM flights f
JOIN airlines a
    ON f.AIRLINE = a.ID
WHERE f.DAY = :day
  AND f.MONTH = :month
  AND f.YEAR = :year
ORDER BY f.ID
"""

QUERY_DELAYED_FLIGHTS_BY_AIRLINE_NAME = f"""
SELECT
    {BASE_RESULT_COLUMNS}
FROM flights f
JOIN airlines a
    ON f.AIRLINE = a.ID
WHERE UPPER(a.AIRLINE) = UPPER(:airline_name)
  AND f.DEPARTURE_DELAY >= :delay_threshold
ORDER BY f.DEPARTURE_DELAY DESC, f.ID
"""

QUERY_DELAYED_FLIGHTS_BY_AIRLINE_IATA = f"""
SELECT
    {BASE_RESULT_COLUMNS}
FROM flights f
JOIN airlines a
    ON f.AIRLINE = a.ID
WHERE CAST(a.IATA_CODE AS TEXT) = :iata_code
  AND f.DEPARTURE_DELAY >= :delay_threshold
ORDER BY f.DEPARTURE_DELAY DESC, f.ID
"""

QUERY_DELAYED_FLIGHTS_BY_AIRLINE_ALIAS = f"""
SELECT
    {BASE_RESULT_COLUMNS}
FROM flights f
JOIN airlines a
    ON f.AIRLINE = a.ID
WHERE CAST(a.ALIAS AS TEXT) = :alias
  AND f.DEPARTURE_DELAY >= :delay_threshold
ORDER BY f.DEPARTURE_DELAY DESC, f.ID
"""

QUERY_DELAYED_FLIGHTS_BY_ORIGIN = f"""
SELECT
    {BASE_RESULT_COLUMNS}
FROM flights f
JOIN airlines a
    ON f.AIRLINE = a.ID
WHERE UPPER(f.ORIGIN_AIRPORT) = UPPER(:origin_airport)
  AND f.DEPARTURE_DELAY >= :delay_threshold
ORDER BY f.DEPARTURE_DELAY DESC, f.ID
"""

QUERY_SEARCH_AIRPORTS_BY_CODE = """
SELECT
    IATA_CODE,
    AIRPORT,
    CITY,
    STATE,
    COUNTRY,
    LATITUDE,
    LONGITUDE
FROM airports
WHERE UPPER(IATA_CODE) = UPPER(:term)
ORDER BY IATA_CODE
"""

QUERY_SEARCH_AIRPORTS_BY_CITY_OR_STATE = """
SELECT
    IATA_CODE,
    AIRPORT,
    CITY,
    STATE,
    COUNTRY,
    LATITUDE,
    LONGITUDE
FROM airports
WHERE UPPER(CITY) LIKE UPPER(:pattern)
   OR UPPER(STATE) LIKE UPPER(:pattern)
ORDER BY COUNTRY, STATE, CITY, AIRPORT
"""


def execute_query(query: str, params: dict | None = None):
    """
    Execute an SQL query and return all result rows.

    If an exception occurs, an empty list is returned.
    """
    if params is None:
        params = {}

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query), params)
            return result.fetchall()
    except Exception as exc:
        print("Query error:", exc)
        return []


def get_flight_by_id(flight_id: int):
    """
    Return the flight matching one database ID.
    """
    return execute_query(QUERY_FLIGHT_BY_ID, {"id": flight_id})


def get_flights_by_date(day: int, month: int, year: int):
    """
    Return all flights for one calendar date.
    """
    params = {
        "day": day,
        "month": str(month),
        "year": str(year),
    }
    return execute_query(QUERY_FLIGHTS_BY_DATE, params)


def get_delayed_flights_by_airline(airline_input: str):
    """
    Return delayed flights for one airline.

    Accepted input types:
    - full airline name
    - airline IATA code
    - airline alias
    """
    normalized_input = airline_input.strip()

    if not normalized_input:
        return []

    threshold_params = {"delay_threshold": DELAY_THRESHOLD_MINUTES}

    if len(normalized_input) <= IATA_CODE_LENGTH and normalized_input.isalnum():
        iata_results = execute_query(
            QUERY_DELAYED_FLIGHTS_BY_AIRLINE_IATA,
            {
                "iata_code": normalized_input.upper(),
                **threshold_params,
            },
        )
        if iata_results:
            return iata_results

        alias_results = execute_query(
            QUERY_DELAYED_FLIGHTS_BY_AIRLINE_ALIAS,
            {
                "alias": normalized_input,
                **threshold_params,
            },
        )
        if alias_results:
            return alias_results

    return execute_query(
        QUERY_DELAYED_FLIGHTS_BY_AIRLINE_NAME,
        {
            "airline_name": normalized_input,
            **threshold_params,
        },
    )


def get_delayed_flights_by_airport(origin_airport: str):
    """
    Return delayed flights for one origin airport IATA code.
    """
    return execute_query(
        QUERY_DELAYED_FLIGHTS_BY_ORIGIN,
        {
            "origin_airport": origin_airport.upper(),
            "delay_threshold": DELAY_THRESHOLD_MINUTES,
        },
    )


def search_airports(term: str):
    """
    Search airports by IATA code, city, or state.
    """
    normalized_term = term.strip()

    if not normalized_term:
        return []

    if len(normalized_term) == IATA_CODE_LENGTH and normalized_term.isalpha():
        return execute_query(
            QUERY_SEARCH_AIRPORTS_BY_CODE,
            {"term": normalized_term.upper()},
        )

    return execute_query(
        QUERY_SEARCH_AIRPORTS_BY_CITY_OR_STATE,
        {"pattern": f"%{normalized_term}%"},
    )