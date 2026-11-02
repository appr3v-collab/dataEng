import sqlite3

import matplotlib.pyplot as plt
import pandas as pd


query = """
    SELECT year, SUM(population) AS total_population
    FROM population_observation
    WHERE country_code="SAU"
    GROUP BY year
    ORDER BY year
"""

with sqlite3.connect("population.db") as connection:
    totals = pd.read_sql_query(query, connection)

totals["total_population_billions"] = (
    totals["total_population"] / 1
)

totals.plot(
    x="year",
    y="total_population_billions",
    title="Total Population in Available Country Records",
    xlabel="Year",
    ylabel="Population (billions)",
    legend=False,
    grid=True,
)

plt.tight_layout()
plt.savefig("population_trend.png")
print("Saved chart to population_trend.png")

