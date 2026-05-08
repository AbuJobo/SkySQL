import csv
import os

from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import visualizations
import flights_data

IATA_LENGTH = 3


def delayed_flights_by_airline():
    """Ask the user for an airline identifier.
    Full name, 2-letter IATA Code, or alias allowed.
    """
    airline_input = input("Enter airline (full name, IATA code, or alias): ").strip()
    results = flights_data.get_delayed_flights_by_airline(airline_input)
    print_results(results)


def resolve_airport_from_user_input():
    """Resolve user input to a single origin airport IATA code.

    Allowed inputs:
    - 3-letter IATA code
    - city name (e.g. 'Nashville')
    - state (e.g. 'CA')

    If multiple airports match, ask the user to choose one.
    """
    term = input("Enter origin airport (IATA, city, or state): ").strip()

    # 3-letter IATA code directly
    if len(term) == 3 and term.isalpha():
        return term.upper()

    matches = flights_data.search_airports(term)

    if not matches:
        print("No airports found for this input.")
        return None

    # Unique match
    if len(matches) == 1:
        row = matches[0]._mapping
        code = row["IATA_CODE"]
        print(f"Using airport {code} - {row['AIRPORT']} ({row['CITY']}, {row['STATE']})")
        return code

    # Multiple matches
    print(f"Found {len(matches)} airports matching '{term}'.")
    choice = input(f"Show all airports in '{term}'? (y/n) ").strip().lower()

    if choice == "y":
        for r in matches:
            m = r._mapping
            print(f"{m['IATA_CODE']}: {m['AIRPORT']} ({m['CITY']}, {m['STATE']}, {m['COUNTRY']})")

    # User selects one IATA code
    valid_codes = {r._mapping["IATA_CODE"].upper() for r in matches}

    while True:
        code_input = input(
            "Enter one of the suggested 3-letter IATA codes (or leave empty to cancel): "
        ).strip().upper()
        if not code_input:
            return None
        if code_input in valid_codes:
            return code_input
        print("IATA code not in list of suggestions, try again.")


def delayed_flights_by_airport():
    """Ask the user for an origin airport.
    Allowed: 3-letter IATA code, city name, or state name.
    """
    iata_code = resolve_airport_from_user_input()
    if not iata_code:
        print("No airport selected.")
        return

    results = flights_data.get_delayed_flights_by_airport(iata_code)
    print_results(results)


def flight_by_id():
    """Ask the user for a numeric flight ID, query the database, and show the result."""
    id_input = None

    while True:
        try:
            id_input = int(input("Enter flight ID: ").strip())
            break
        except ValueError:
            print("Try again...")

    results = flights_data.get_flight_by_id(id_input)
    print_results(results)


def flights_by_date():
    """Ask the user for a date (DD/MM/YYYY), query the database, and show results."""
    date = None

    while True:
        try:
            date_input = input("Enter date in DD/MM/YYYY format: ").strip()
            date = datetime.strptime(date_input, "%d/%m/%Y")
            break
        except ValueError as e:
            print("Try again...", e)

    results = flights_data.get_flights_by_date(date.day, date.month, date.year)
    print_results(results)


def export_results_to_csv(results, filename):
    """Export query results to a CSV file inside ./results."""
    if not results:
        print("No data to export.")
        return

    output_dir = "results"  # folder in project directory
    os.makedirs(output_dir, exist_ok=True)

    full_path = os.path.join(output_dir, filename)

    rows = [dict(row._mapping) for row in results]
    fieldnames = list(rows[0].keys())

    with open(full_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Data exported to {full_path}")


def print_results(results):
    """Print query results and optionally export them to CSV."""
    if results is None:
        results = []

    for row in results:
        result = row._mapping

        try:
            delay = int(result["DELAY"]) if result["DELAY"] not in (None, "") else 0
            origin = result["ORIGIN_AIRPORT"]
            dest = result["DESTINATION_AIRPORT"]
            airline = result["AIRLINE"]
            flight_id = result["ID"]
        except (ValueError, KeyError, SQLAlchemyError) as e:
            print("Error showing results:", e)
            return

        if delay >= 20:
            print(f"{flight_id}. {origin} -> {dest} by {airline}, Delay: {delay} Minutes")
        else:
            print(f"{flight_id}. {origin} -> {dest} by {airline}")
    print(f"Got {len(results)} results.")
    export_choice = input("Would you like to export this data to a CSV file? (y/n) ").strip().lower()

    if export_choice == "y":
        filename = input("Enter CSV filename: ").strip()
        if filename:
            export_results_to_csv(results, filename)
        else:
            print("Invalid filename. Export canceled.")

def create_visualizations():
    """
    Create and save visualizations.
    """
    print("\nVisualization Menu:")
    print("1. Percentage of delayed flights per airline")
    print("2. Back")

    while True:
        choice = input("Choose an option: ").strip()

        if choice == "1":
            visualizations.plot_delayed_percentage_by_airline()
            return
        elif choice == "2":
            return
        else:
            print("Try again...")


def show_menu_and_get_input():
    """Show the menu, validate the user's selection, and return the function."""
    print("\nMenu:")
    for key, value in FUNCTIONS.items():
        print(f"{key}. {value[1]}")

    while True:
        try:
            choice = int(input().strip())
            if choice in FUNCTIONS:
                return FUNCTIONS[choice][0]
        except ValueError:
            pass
        print("Try again...")


FUNCTIONS = {
    1: (flight_by_id, "Show flight by ID"),
    2: (flights_by_date, "Show flights by date"),
    3: (delayed_flights_by_airline, "Delayed flights by airline (full name / IATA / alias)"),
    4: (delayed_flights_by_airport, "Delayed flights by origin airport"),
    5: (create_visualizations, "Create visualizations"),
    6: (quit, "Exit"),
}


def main():
    """Main program loop."""
    while True:
        choice_func = show_menu_and_get_input()
        choice_func()


if __name__ == "__main__":
    main()