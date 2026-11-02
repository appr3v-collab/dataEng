import sqlite3

query = """
    SELECT year, SUM(population) AS total_population, COUNT(*) AS countries
    FROM population_observation
    GROUP BY year
    ORDER BY year
"""

with sqlite3.connect("population.db") as connection:
    rows = connection.execute(query).fetchall()

print("Year | Total population in available records | Countries with data")
for year, total, country_count in rows:
    print(f"{year} | {total:,} | {country_count}")

