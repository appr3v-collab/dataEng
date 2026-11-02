import sqlite3


with sqlite3.connect("population.db") as connection:
    rows = connection.execute("""
        SELECT country, latest_year, latest_population, change_percent
        FROM population_report
        ORDER BY latest_population DESC
        LIMIT 5
    """).fetchall()

print("Top 5 countries by latest recorded population:")

for country, year, population, change_percent in rows:
    change = f"{change_percent:.2f}%" if change_percent is not None else "N/A"
    print(f"{country}: {population:,} in {year} (change: {change})")

