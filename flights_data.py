from sqlalchemy import create_engine, text

DELAY_THRESHOLD = 20

# Einzelner Flug per ID
QUERY_FLIGHT_BY_ID = """
SELECT
    flights.ID,
    flights.ID AS FLIGHT_ID,
    flights.ORIGIN_AIRPORT,
    flights.DESTINATION_AIRPORT,
    airlines.AIRLINE AS AIRLINE,
    flights.DEPARTURE_DELAY AS DELAY
FROM flights
JOIN airlines ON flights.AIRLINE = airlines.ID
WHERE flights.ID = :id
"""

# Flüge nach Datum
QUERY_FLIGHTS_BY_DATE = """
SELECT
    flights.ID,
    flights.ID AS FLIGHT_ID,
    flights.ORIGIN_AIRPORT,
    flights.DESTINATION_AIRPORT,
    airlines.AIRLINE AS AIRLINE,
    flights.DEPARTURE_DELAY AS DELAY
FROM flights
JOIN airlines ON flights.AIRLINE = airlines.ID
WHERE CAST(flights.DAY AS INTEGER) = :day
  AND CAST(flights.MONTH AS INTEGER) = :month
  AND CAST(flights.YEAR AS INTEGER) = :year
ORDER BY flights.ID
"""

# Verspätete Flüge nach Airline – Name, IATA oder Alias
QUERY_DELAYED_FLIGHTS_BY_AIRLINE = """
SELECT
    flights.ID,
    flights.ID AS FLIGHT_ID,
    flights.ORIGIN_AIRPORT,
    flights.DESTINATION_AIRPORT,
    airlines.AIRLINE AS AIRLINE,
    flights.DEPARTURE_DELAY AS DELAY
FROM flights
JOIN airlines ON flights.AIRLINE = airlines.ID
WHERE (
    LOWER(airlines.AIRLINE)   = LOWER(:airline)
    OR UPPER(airlines.IATA_CODE) = UPPER(:airline)
    OR LOWER(airlines.ALIAS)  = LOWER(:airline)
)
  AND flights.DEPARTURE_DELAY IS NOT NULL
  AND TRIM(CAST(flights.DEPARTURE_DELAY AS TEXT)) != ''
  AND CAST(flights.DEPARTURE_DELAY AS INTEGER) >= :delay_threshold
ORDER BY CAST(flights.DEPARTURE_DELAY AS INTEGER) DESC, flights.ID
"""

# Verspätete Flüge nach Abflug-Airport (IATA)
QUERY_DELAYED_FLIGHTS_BY_AIRPORT = """
SELECT
    flights.ID,
    flights.ID AS FLIGHT_ID,
    flights.ORIGIN_AIRPORT,
    flights.DESTINATION_AIRPORT,
    airlines.AIRLINE AS AIRLINE,
    flights.DEPARTURE_DELAY AS DELAY
FROM flights
JOIN airlines ON flights.AIRLINE = airlines.ID
WHERE UPPER(flights.ORIGIN_AIRPORT) = UPPER(:airport)
  AND flights.DEPARTURE_DELAY IS NOT NULL
  AND TRIM(CAST(flights.DEPARTURE_DELAY AS TEXT)) != ''
  AND CAST(flights.DEPARTURE_DELAY AS INTEGER) >= :delay_threshold
ORDER BY CAST(flights.DEPARTURE_DELAY AS INTEGER) DESC, flights.ID
"""

# Airport-Suche nach IATA, Stadt oder State
QUERY_AIRPORT_SEARCH = """
SELECT
    IATA_CODE,
    AIRPORT,
    CITY,
    STATE,
    COUNTRY
FROM airports
WHERE
      UPPER(IATA_CODE) = UPPER(:term)
   OR UPPER(CITY)      = UPPER(:term)
   OR UPPER(STATE)     = UPPER(:term)
ORDER BY IATA_CODE
"""

DATABASE_URL = "sqlite:///data/flights_v2.sqlite3"
engine = create_engine(DATABASE_URL)


def execute_query(query, params):
    """Execute a parameterized SQL query and return all matching rows."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchall()
    except Exception as e:
        print("Query error:", e)
        return []


def get_flight_by_id(flight_id):
    """Return the flight record for one specific flight ID."""
    params = {"id": flight_id}
    return execute_query(QUERY_FLIGHT_BY_ID, params)


def get_flights_by_date(day, month, year):
    """Return all flights for a given day, month, and year."""
    params = {"day": day, "month": month, "year": year}
    return execute_query(QUERY_FLIGHTS_BY_DATE, params)


def get_delayed_flights_by_airline(airline_name):
    """Return all delayed flights for one airline (name, IATA code, or alias)."""
    params = {"airline": airline_name, "delay_threshold": DELAY_THRESHOLD}
    return execute_query(QUERY_DELAYED_FLIGHTS_BY_AIRLINE, params)


def get_delayed_flights_by_airport(airport_code):
    """Return all delayed flights departing from one origin airport (IATA)."""
    params = {"airport": airport_code, "delay_threshold": DELAY_THRESHOLD}
    return execute_query(QUERY_DELAYED_FLIGHTS_BY_AIRPORT, params)


def search_airports(term):
    """Search airports by IATA code, city or state."""
    params = {"term": term}
    return execute_query(QUERY_AIRPORT_SEARCH, params)