from unittest import TestCase
import lightroom_sync as lrsync
import sqlite3
import os
from pathlib import Path


class TestDatabase(TestCase):
    def setUp(self):
        self.test_db_name = "test_db.db"
        self.test_db = lrsync.Database(self.test_db_name)
        self.test_catalog = "test_catalog.lrcat"
        Path(self.test_catalog).write_text("test catalog")

    def tearDown(self):
        test_files = [self.test_db_name,
                      self.test_catalog]
        for f in test_files:
            if os.path.isfile(f):
                os.remove(f)

    def test_init_db(self):
        self.assertEqual(self.test_db.db, self.test_db_name)

    def test_init_connect(self):
        self.assertIsInstance(self.test_db.conn, sqlite3.Connection)

    def test_init_cursor(self):
        self.assertIsInstance(self.test_db.cursor, sqlite3.Cursor)

    def test_create_tables(self):
        pass
