import os
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd

DATABASE_PATH = "data/flights_v2.sqlite3"
RESULTS_DIR = "results"


def plot_delayed_percentage_by_airline():
    """
    Create a bar chart showing the percentage of delayed flights per airline.
    A flight is delayed if DEPARTURE_DELAY >= 20.
    Empty or NULL delay values are not counted as delayed.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)

    query = """
    SELECT
        a.AIRLINE AS airline,
        COUNT(*) AS total_flights,
        SUM(
            CASE
                WHEN f.DEPARTURE_DELAY IS NOT NULL
                 AND TRIM(CAST(f.DEPARTURE_DELAY AS TEXT)) != ''
                 AND CAST(f.DEPARTURE_DELAY AS INTEGER) >= 20
                THEN 1
                ELSE 0
            END
        ) AS delayed_flights
    FROM flights f
    JOIN airlines a ON f.AIRLINE = a.ID
    GROUP BY a.AIRLINE
    ORDER BY airline
    """

    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["delayed_pct"] = (df["delayed_flights"] / df["total_flights"]) * 100
    df = df.sort_values("delayed_pct", ascending=False)

    plt.figure(figsize=(12, 6))
    plt.bar(df["airline"], df["delayed_pct"])
    plt.xticks(rotation=75, ha="right")
    plt.ylabel("Delayed flights (%)")
    plt.xlabel("Airline")
    plt.title("Percentage of delayed flights per airline")
    plt.tight_layout()

    output_file = os.path.join(RESULTS_DIR, "delayed_percentage_by_airline.png")
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"Chart saved to {output_file}")