import sqlite3

query = """
    SELECT country, year, population,
           LAG(population) OVER (
               PARTITION BY country_code
               ORDER BY year
           ) AS previous_population
    FROM population_observation
    ORDER BY country, year
"""

with sqlite3.connect("population.db") as connection:
    rows = connection.execute(query).fetchall()

print("Country | Year | Population | Change from prior available year")
for country, year, population, previous in rows:
    if previous is None:
        change = "N/A"
    else:
        change = f"{(population - previous) / previous * 100:.2f}%"

    print(f"{country} | {year} | {population:,} | {change}")

