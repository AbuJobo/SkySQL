"""
Console entry point for the flight database project.
This module provides a menu-driven CLI for querying flights, resolving airports,
exporting result sets to CSV, and generating visualizations.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys

from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

import flights_data
import visualizations

IATA_LENGTH = 3
DELAY_THRESHOLD_MINUTES = 20
RESULTS_DIRECTORY = "results"
DATE_INPUT_FORMAT = "%d/%m/%Y"
CSV_EXTENSION = ".csv"


def sanitize_filename_part(value: str) -> str:
    """
    Sanitize a filename fragment so it is safe for file creation.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "export"


def normalize_date_input(date_input: str) -> str:
    """
    Normalize a date input to DD/MM/YYYY.

    Example:
    - 12012015 -> 12/01/2015
    - 12/01/2015 -> 12/01/2015
    """
    compact = re.sub(r"\D", "", date_input)

    if len(compact) == 8:
        return f"{compact[0:2]}/{compact[2:4]}/{compact[4:8]}"

    return date_input.strip()


def build_export_filename(query_type: str, query_value: str, result_count: int) -> str:
    """
    Build an automatic CSV filename based on query type, input value, and result count.

    Examples:
    - flight_ID2_1.csv
    - flights_20150112_143.csv
    - flights_AA_delayed_departure_38.csv
    - flights_JFK_delayed_22.csv
    """
    normalized_value = sanitize_filename_part(query_value)

    filename_map = {
        "flight_by_id": f"flight_ID{normalized_value}_{result_count}",
        "flights_by_date": f"flights_{normalized_value}_{result_count}",
        "delayed_flights_by_airline": f"flights_{normalized_value}_delayed_departure_{result_count}",
        "delayed_flights_by_airport": f"flights_{normalized_value}_delayed_{result_count}",
    }

    base_name = filename_map.get(query_type, f"flights_export_{normalized_value}_{result_count}")
    return f"{base_name}{CSV_EXTENSION}"


def delayed_flights_by_airline() -> None:
    """
    Ask the user for an airline identifier and show matching delayed departures.
    """
    airline_input = input("Enter airline (full name, IATA code, or alias): ").strip()
    results = flights_data.get_delayed_flights_by_airline(airline_input)
    print_results(results, query_type="delayed_flights_by_airline", query_value=airline_input.upper())


def resolve_airport_from_user_input() -> str | None:
    """
    Resolve user input to one origin airport IATA code.

    Allowed inputs:
    - 3-letter IATA code
    - city name
    - state
    """
    term = input("Enter origin airport (IATA, city, or state): ").strip()

    if len(term) == IATA_LENGTH and term.isalpha():
        return term.upper()

    matches = flights_data.search_airports(term)

    if not matches:
        print("No airports found for this input.")
        return None

    if len(matches) == 1:
        row = matches[0]._mapping
        code = row["IATA_CODE"]
        print(f"Using airport {code} - {row['AIRPORT']} ({row['CITY']}, {row['STATE']})")
        return code

    print(f"Found {len(matches)} airports matching '{term}'.")
    choice = input(f"Show all airports in '{term}'? (y/n) ").strip().lower()

    if choice == "y":
        for result_row in matches:
            mapped = result_row._mapping
            print(
                f"{mapped['IATA_CODE']}: {mapped['AIRPORT']} "
                f"({mapped['CITY']}, {mapped['STATE']}, {mapped['COUNTRY']})"
            )

    valid_codes = {result_row._mapping["IATA_CODE"].upper() for result_row in matches}

    while True:
        code_input = input(
            "Enter one of the suggested 3-letter IATA codes (or leave empty to cancel): "
        ).strip().upper()

        if not code_input:
            return None

        if code_input in valid_codes:
            return code_input

        print("IATA code not in list of suggestions, try again.")


def delayed_flights_by_airport() -> None:
    """
    Ask the user for an origin airport and show delayed departures.
    """
    iata_code = resolve_airport_from_user_input()
    if not iata_code:
        print("No airport selected.")
        return

    results = flights_data.get_delayed_flights_by_airport(iata_code)
    print_results(results, query_type="delayed_flights_by_airport", query_value=iata_code)


def flight_by_id() -> None:
    """
    Ask the user for a numeric flight ID and show the matching flight.
    """
    while True:
        try:
            flight_id = int(input("Enter flight ID: ").strip())
            break
        except ValueError:
            print("Try again...")

    results = flights_data.get_flight_by_id(flight_id)
    print_results(results, query_type="flight_by_id", query_value=str(flight_id))


def flights_by_date() -> None:
    """
    Ask the user for a date and show matching flights.

    The function accepts DD/MM/YYYY directly and also auto-formats 8 digits
    into DD/MM/YYYY by inserting slashes automatically.
    """
    while True:
        try:
            raw_date_input = input("Enter date in DD/MM/YYYY format: ").strip()
            normalized_date_input = normalize_date_input(raw_date_input)
            date_value = datetime.strptime(normalized_date_input, DATE_INPUT_FORMAT)
            break
        except ValueError as exc:
            print("Try again...", exc)

    results = flights_data.get_flights_by_date(date_value.day, date_value.month, date_value.year)
    export_value = date_value.strftime("%Y%m%d")
    print_results(results, query_type="flights_by_date", query_value=export_value)


def export_results_to_csv(results, filename: str) -> None:
    """
    Export query results to a CSV file inside the results directory.
    """
    if not results:
        print("No data to export.")
        return

    os.makedirs(RESULTS_DIRECTORY, exist_ok=True)
    full_path = os.path.join(RESULTS_DIRECTORY, filename)

    rows = [dict(row._mapping) for row in results]
    field_names = list(rows[0].keys())

    with open(full_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Data exported to {full_path}")


def print_results(results, query_type: str, query_value: str) -> None:
    """
    Print query results and optionally export them to CSV.

    The function uses DEPARTURE_DELAY only, matching the database schema.
    The export filename is generated automatically.
    """
    if results is None:
        results = []

    for row in results:
        result = row._mapping

        try:
            departure_delay = (
                int(result["DEPARTURE_DELAY"])
                if result["DEPARTURE_DELAY"] not in (None, "")
                else 0
            )
            origin = result["ORIGIN_AIRPORT"]
            destination = result["DESTINATION_AIRPORT"]
            airline = result["AIRLINE"]
            flight_id = result["ID"]
        except (ValueError, KeyError, SQLAlchemyError) as exc:
            print("Error showing results:", exc)
            return

        if departure_delay >= DELAY_THRESHOLD_MINUTES:
            print(
                f"{flight_id}. {origin} -> {destination} by {airline}, "
                f"Departure delay: {departure_delay} minutes"
            )
        else:
            print(f"{flight_id}. {origin} -> {destination} by {airline}")

    result_count = len(results)
    print(f"Got {result_count} results.")

    if not results:
        return

    export_choice = input("Would you like to export this data to a CSV file? (y/n) ").strip().lower()

    if export_choice == "y":
        filename = build_export_filename(query_type, query_value, result_count)
        export_results_to_csv(results, filename)


def create_visualizations() -> None:
    """
    Show the visualization menu and generate selected charts.
    """
    print("\nVisualization Menu:")
    print("1. Percentage of delayed flights per airline")
    print("2. Back")

    while True:
        choice = input("Choose an option: ").strip()

        if choice == "1":
            visualizations.plot_delayed_percentage_by_airline()
            return
        if choice == "2":
            return

        print("Try again...")

def open_visualization_tuner() -> None:
    """
    Launch the Streamlit-based visualization guide tuner in a separate process.
    """
    try:
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "guide_tuner_app.py"],
        )
        print("Opening visualization tuner in your browser...")
    except Exception as exc:
        print("Could not start visualization tuner:", exc)

def show_menu_and_get_input():
    """
    Show the main menu and return the selected function.
    """
    print("\nMenu:")
    for key, value in FUNCTIONS.items():
        print(f"{key}. {value[1]}")
    print("\n Enter Your choice here:")
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
    3: (delayed_flights_by_airline, "Delayed flights by airline (full name / airline IATA code / alias)"),
    4: (delayed_flights_by_airport, "Delayed flights by origin (airport IATA code / city / state)"),
    5: (create_visualizations, "Create visualizations"),
    6: (open_visualization_tuner, "Open visualization tuner (Streamlit, runs in parallel)"),
    7: (quit, "Exit"),
}


def main() -> None:
    """
    Run the main command-line loop.
    """
    while True:
        selected_function = show_menu_and_get_input()
        selected_function()


if __name__ == "__main__":
    main()