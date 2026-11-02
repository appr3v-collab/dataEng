import unittest
import sqlite3
import tempfile
from pathlib import Path
from pipeline import load_observations

from pipeline import percent_change, transform_records


class TestObservationLoad(unittest.TestCase):
    def test_rerunning_load_does_not_duplicate_rows(self):
        records = [
            {
                "value": 100,
                "countryiso3code": "TST",
                "country": {
                    "value": "Testland",
                    "region": {"value": "Europe"},
                },
                "date": "2021",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "test.db"

            load_observations(records, database_path)
            load_observations(records, database_path)

            with sqlite3.connect(database_path) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM population_observation"
                ).fetchone()[0]

            self.assertEqual(count, 1)



class TestPercentChange(unittest.TestCase):
    def test_increase(self):
        self.assertEqual(percent_change(110, 100), 10.0)

    def test_decrease(self):
        self.assertEqual(percent_change(90, 100), -10.0)

    def test_missing_previous_value(self):
        self.assertIsNone(percent_change(110, None))

    def test_zero_previous_value(self):
        self.assertIsNone(percent_change(110, 0))


class TestTransformRecords(unittest.TestCase):
    def test_keeps_latest_year_and_calculates_change(self):
        records = [
            {
                "value": 100,
                "countryiso3code": "TST",
                "country": {"value": "Testland"},
                "date": "2020",
            },
            {
                "value": 110,
                "countryiso3code": "TST",
                "country": {"value": "Testland"},
                "date": "2021",
            },
        ]

        result = transform_records(records)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["latest_year"], 2021)
        self.assertEqual(result[0]["latest_population"], 110)
        self.assertEqual(result[0]["change_percent"], 10.0)
        
    def test_skips_aggregates_and_blank_country_codes(self):
        records = [
            {
                "value": 1000,
                "countryiso3code": "TST",
                "country": {
                    "value": "Testland",
                    "region": {"value": "Europe"},
                },
                "date": "2021",
            },
            {
                "value": 2000,
                "countryiso3code": "WLD",
                "country": {
                    "value": "World",
                    "region": {"value": "Aggregates"},
                },
                "date": "2021",
            },
            {
                "value": 3000,
                "countryiso3code": "",
                "country": {"value": "Unknown"},
                "date": "2021",
            },
        ]

        result = transform_records(records)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["country_code"], "TST")


if __name__ == "__main__":
    unittest.main()

