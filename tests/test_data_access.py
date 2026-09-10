from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import sqlite3
import unittest

import functions


class DataAccessTests(unittest.TestCase):
    def test_query_connection_cannot_modify_data(self):
        with TemporaryDirectory() as directory:
            database = Path(directory) / 'fixture.db'
            connection = sqlite3.connect(database)
            connection.execute('CREATE TABLE records (value TEXT)')
            connection.execute("INSERT INTO records VALUES ('preserved')")
            connection.commit()
            connection.close()
            with patch.object(functions, 'DATABASE_PATH', database):
                with self.assertRaises(sqlite3.OperationalError):
                    functions._read_bus_rows('DELETE FROM records')
                rows = functions._read_bus_rows('SELECT value FROM records')
            self.assertEqual(rows[0]['value'], 'preserved')

    def test_packaged_database_does_not_depend_on_the_working_directory(self):
        original = Path.cwd()
        with TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                rows = functions._read_bus_rows('SELECT COUNT(*) AS count FROM Bus_Stops')
                self.assertGreater(rows[0]['count'], 0)
            finally:
                os.chdir(original)


if __name__ == '__main__':
    unittest.main()
