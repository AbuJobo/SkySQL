import csv
import os
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

import flights_data

IATA_LENGTH = 3


def delayed_flights_by_airline():
    """
    Ask the user for an airline identifier.
    Full name, 2-letter IATA Code, or alias allowed.
    """
    airline_input = input("Enter airline (full name, IATA code, or alias): ").strip()
    results = flights_data.get_delayed_flights_by_airline(airline_input)
    print_results(results)


def delayed_flights_by_airport():
    """
    Ask the user for a 3-letter origin airport code, validate it,
    then query the database and show the results.
    """
    airport_input = ""

    while True:
        airport_input = input("Enter origin airport IATA code: ").strip().upper()
        if airport_input.isalpha() and len(airport_input) == IATA_LENGTH:
            break
        print("Try again...")

    results = flights_data.get_delayed_flights_by_airport(airport_input)
    print_results(results)


def flight_by_id():
    """
    Ask the user for a numeric flight ID, query the database,
    and show the result.
    """
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
    """
    Ask the user for a date in DD/MM/YYYY format, validate it,
    then query the database and show the matching flights.
    """
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
    """
    Export query results to a CSV file inside ../results.
    """
    if not results:
        print("No data to export.")
        return

    output_dir = os.path.join("..", "results")
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
    """
    Print query results to the terminal.
    After printing, optionally export the data to CSV.
    """
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


def show_menu_and_get_input():
    """
    Show the menu, validate the user's selection,
    and return the function that should be executed.
    """
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
    3: (delayed_flights_by_airline, "Delayed flights by airline (full name, IATA code, or alias)"),
    4: (delayed_flights_by_airport, "Delayed flights by origin airport"),
    5: (quit, "Exit"),
}


def main():
    """
    Main program loop.
    Keep showing the menu until the user chooses Exit.
    """
    while True:
        choice_func = show_menu_and_get_input()
        choice_func()


if __name__ == "__main__":
    main()