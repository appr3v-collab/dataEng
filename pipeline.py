import csv
import logging
import sqlite3
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import requests


API_URL = (
    "https://api.worldbank.org/v2/country/all/"
    "indicator/SP.POP.TOTL"
)

def create_http_session():
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def percent_change(latest, previous):
    """Return percentage change, or None when it can't be calculated."""
    if previous is None or previous == 0:
        return None

    return round((latest - previous) / previous * 100, 2)


def fetch_records():
    """Fetch every page of population records from the World Bank API."""
    logging.info("Fetching population data for all API locations")
    
    session = create_http_session()

    all_records = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        response = session.get(
            API_URL,
            params={
                "format": "json",
                "per_page": 1000,
                "page": page,
            },
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()

        if len(payload) < 2 or payload[1] is None:
            break

        metadata, page_records = payload
        all_records.extend(page_records)
        total_pages = int(metadata["pages"])
        page += 1

    if not all_records:
        raise ValueError("The API returned no population records.")

    logging.info("Fetched %d records across %d pages", len(all_records), total_pages)
    return all_records

def transform_records(records):
    """Validate records and create one report row per country."""
    by_country = defaultdict(list)
    skipped_missing_value=0
    skipped_aggregate=0

    for record in records:
        if record["value"] is None:
            skipped_missing_value+=1
            continue

        country_code = record["countryiso3code"]
        #region = record["country"]["region"]["value"]
        
        region = record["country"].get("region", {}).get("value", "")
        
        # The API's "all" endpoint includes regional aggregates.
        if not country_code or region == "Aggregates":
           skipped_aggregate+=1
           continue

        by_country[country_code].append({
            "country": record["country"]["value"],
            "year": int(record["date"]),
            "population": int(record["value"]),
        })

    if not by_country:
        raise ValueError("No usable population records were returned.")
        
    logging.info("Skipped %d records without values and %d aggregate or blank-code records",skipped_missing_value,skipped_aggregate)

    report = []

    for country_code, country_records in by_country.items():
        years = [row["year"] for row in country_records]
      #  print(country_code+"...............")
        if len(years) != len(set(years)):
            raise ValueError(f"Duplicate year found for {country_code}")

        if any(row["population"] < 0 for row in country_records):
           raise ValueError(f"Negative population found for {country_code}")

        country_records.sort(key=lambda row: row["year"])
        latest = country_records[-1]
        previous = country_records[-2] if len(country_records) >= 2 else None

        report.append({
            "country": latest["country"],
            "country_code": country_code,
            "latest_year": latest["year"],
            "latest_population": latest["population"],
            "previous_year": previous["year"] if previous else None,
            "change_percent": percent_change(
                latest["population"],
                previous["population"] if previous else None,
            ),
        })

    report.sort(key=lambda row: row["country"])
    return report


def save_csv(report):
    """Write the transformed report to a CSV file."""
    columns = [
        "country",
        "country_code",
        "latest_year",
        "latest_population",
        "previous_year",
        "change_percent",
    ]

    with open("population_report.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report)

    logging.info("Wrote %d countries to population_report.csv", len(report))


def load_database(report):
    """Load the report into SQLite, updating countries on reruns."""
    with sqlite3.connect("population.db") as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS population_report (
                country_code TEXT PRIMARY KEY,
                country TEXT NOT NULL,
                latest_year INTEGER NOT NULL,
                latest_population INTEGER NOT NULL,
                previous_year INTEGER,
                change_percent REAL
            )
        """)

        connection.executemany("""
            INSERT INTO population_report (
                country_code,
                country,
                latest_year,
                latest_population,
                previous_year,
                change_percent
            )
            VALUES (
                :country_code,
                :country,
                :latest_year,
                :latest_population,
                :previous_year,
                :change_percent
            )
            ON CONFLICT(country_code) DO UPDATE SET
                country = excluded.country,
                latest_year = excluded.latest_year,
                latest_population = excluded.latest_population,
                previous_year = excluded.previous_year,
                change_percent = excluded.change_percent
        """, report)

    logging.info("Loaded %d countries into population.db", len(report))


def load_observations(records, database_path="population.db"):
    """Store valid country-year observations in SQLite."""
    observations = []

    for record in records:
        if record["value"] is None:
            continue

        country_code = record["countryiso3code"]
        region = record["country"].get("region", {}).get("value", "")

        if not country_code or region == "Aggregates":
            continue

        observations.append((
            country_code,
            record["country"]["value"],
            int(record["date"]),
            int(record["value"]),
        ))

    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS population_observation (
                country_code TEXT NOT NULL,
                country TEXT NOT NULL,
                year INTEGER NOT NULL,
                population INTEGER NOT NULL,
                PRIMARY KEY (country_code, year)
            )
        """)

        connection.executemany("""
            INSERT INTO population_observation
                (country_code, country, year, population)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(country_code, year) DO UPDATE SET
                country = excluded.country,
                population = excluded.population
        """, observations)

    logging.info("Loaded %d annual observations", len(observations))




def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
           logging.StreamHandler(),
           logging.FileHandler("pipeline.log", encoding="utf-8"),
        ],
    )

    try:
        records = fetch_records()
        report = transform_records(records)
        load_observations(records)
        save_csv(report)
        load_database(report)
        logging.info("Pipeline finished successfully")
    except (requests.RequestException, ValueError, sqlite3.Error, OSError):
        logging.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    main()

