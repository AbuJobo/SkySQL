from sqlalchemy import create_engine, text
DELAY_THRESHOLD = 20

# Query used by menu option 1.
# It returns one flight by its numeric ID together with the airline name.
# The selected column aliases match the keys expected by main.py:
# ID, FLIGHT_ID, ORIGIN_AIRPORT, DESTINATION_AIRPORT, AIRLINE, DELAY

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

# Query used by menu option 2.
# It returns all flights for a given calendar date.
# DAY, MONTH, and YEAR are cast to integers so that user input from Python
# can be compared safely even if the SQLite columns are stored as text.

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

# Query used by menu option 3.
# It returns delayed flights for one airline name.
# Important rules implemented here:
# - airline name match is case-insensitive
# - NULL or empty delay values are ignored
# - only delays of 20 minutes or more are treated as delayed

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
    LOWER(airlines.AIRLINE) = LOWER(:airline)
    OR UPPER(airlines.IATA_CODE) = UPPER(:airline)
    OR LOWER(airlines.ALIAS) = LOWER(:airline)
)
  AND flights.DEPARTURE_DELAY IS NOT NULL
  AND TRIM(CAST(flights.DEPARTURE_DELAY AS TEXT)) != ''
  AND CAST(flights.DEPARTURE_DELAY AS INTEGER) >= :delay_threshold
ORDER BY CAST(flights.DEPARTURE_DELAY AS INTEGER) DESC, flights.ID
"""

# Query used by menu option 4.
# It returns delayed flights for one origin airport.
# The airport code comparison is case-insensitive for easier user input.
# As above, only real delays of at least 20 minutes are included.

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

# Define the database URL
DATABASE_URL = "sqlite:///data/flights_v2.sqlite3"

# Create the engine
engine = create_engine(DATABASE_URL)


def execute_query(query, params):
    """
    Execute an SQL query with the params provided in a dictionary,
    and returns a list of records (dictionary-like objects).
    If an exception was raised, print the error, and return an empty list.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            return result.fetchall()
    except Exception as e:
        print("Query error:", e)
        return []


def get_flight_by_id(flight_id):
    """
    Searches for flight details using flight ID.
    If the flight was found, returns a list with a single record.
    Otherwise an empty list is returned
    """
    params = {'id': flight_id}
    return execute_query(QUERY_FLIGHT_BY_ID, params)

def get_flights_by_date(day, month, year):
    """
    Searches for all flights matching DD and MM and YYYY.
    :return: a list wit all matching flights
    """
    params = {"day": day, "month": month, "year": year}
    return execute_query(QUERY_FLIGHTS_BY_DATE, params)


def get_delayed_flights_by_airline(airline_name):
    """
    :return: Returns all delayed flights for one airline.
    A flight counts as delayed only when DEPARTURE_DELAY is 20 minutes or more as defined above.
    Missing values (NULL or empty strings) are ignored and are not treated as delay.
    :param airline_name:
    """
    params = {"airline": airline_name, "delay_threshold": DELAY_THRESHOLD}
    return execute_query(QUERY_DELAYED_FLIGHTS_BY_AIRLINE, params)


def get_delayed_flights_by_airport(airport_code):
    """
    :return: Returns all delayed flights departing from one airport.
    :param airport_code: 3 Letter IATA Code
    """
    params = {"airport": airport_code, "delay_threshold": DELAY_THRESHOLD}
    return execute_query(QUERY_DELAYED_FLIGHTS_BY_AIRPORT, params)
    