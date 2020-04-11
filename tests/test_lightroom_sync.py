from unittest import TestCase
from lightroom_sync import lightroom_sync
import sqlite3
import os
from pathlib import Path
import time


class TestLightroomSync(TestCase):
    def setUp(self):
        # Set up test database
        self.test_db_name = "test_db.db"
        self.lrsync = lightroom_sync.LightroomSync(self.test_db_name)
        self.cur = self.lrsync.cur

        self.lrsync.cur.execute(""" -- Create catalogs table
                                    CREATE TABLE IF NOT EXISTS catalogs(
                                        catalog_id INTEGER PRIMARY KEY,
                                        catalog_name TEXT NOT NULL UNIQUE,
                                        last_sync INTEGER
                                    );
                                    """)
        self.lrsync.cur.execute("""
                            -- Create paths table
                            CREATE TABLE IF NOT EXISTS paths(
                                path_id INTEGER PRIMARY KEY,
                                path text UNIQUE,
                                catalog_id INTEGER,
                                FOREIGN KEY(catalog_id) REFERENCES catalogs(catalog_id)
                            );
                        """)

        # Create test catalog
        self.test_catalog_name = "test_catalog_v013.lrcat"

        self.test_catalog_a = Path("test_a") / self.test_catalog_name
        self.test_catalog_b = Path("test_b") / self.test_catalog_name
        self.test_catalog_c = Path("test_c") / "test_catalog_c_v013.lrcat"
        self.not_test_catalog = Path("test_backups") / ("not_" + self.test_catalog_name)

        test_catalogs = [self.test_catalog_a,
                         self.test_catalog_b,
                         self.test_catalog_c,
                         self.not_test_catalog]

        # Create catalogs
        for c in test_catalogs:
            c.parent.mkdir(exist_ok=True)
            c.write_text(str(c))

        # Catalog db lists
        self.test_catalogs = [(1, self.test_catalog_a.stem, None),
                              (2, self.test_catalog_c.stem, None)]
        self.test_paths = [(1, str(self.test_catalog_a.resolve()), 1),
                           (2, str(self.test_catalog_b.resolve()), 1)]

        # Setup database
        self.cur.execute("INSERT INTO catalogs(catalog_id, catalog_name)"
                         f"VALUES (1, '{self.test_catalog_a.stem}')")
        self.cur.execute("INSERT INTO catalogs(catalog_id, catalog_name)"
                         f"VALUES (2, '{self.test_catalog_c.stem}')")
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         f"VALUES (1, '{self.test_catalog_a.resolve()}')")
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         f"VALUES (1, '{self.test_catalog_b.resolve()}')")
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         f"VALUES (2, '{self.test_catalog_c.resolve()}')")

    def tearDown(self):
        test_files = [self.test_db_name,
                      self.test_catalog_a.resolve(),
                      self.test_catalog_b.resolve(),
                      self.test_catalog_c.resolve(),
                      self.not_test_catalog.resolve()]

        for f in test_files:
            p = Path(f)
            if p.is_file():
                p.unlink()

            if str(p.parent) is not ".":
                if p.parent.is_dir():
                    p.parent.rmdir()

    #
    # Test init
    #
    def test_init_db(self):
        self.assertEqual(self.lrsync.db, self.test_db_name)

    def test_init_connect(self):
        self.assertIsInstance(self.lrsync.conn, sqlite3.Connection)

    def test_init_cursor(self):
        self.assertIsInstance(self.lrsync.cur, sqlite3.Cursor)

    #
    # Test class methods
    #
    def test_scan_for_catalogs(self):
        path = Path()
        catalogs_a = lightroom_sync.scan_for_catalogs(path)
        list_a = [str(x.resolve()) for x in catalogs_a]
        list_a.sort()

        catalogs_b = [self.test_catalog_a, self.test_catalog_b, self.test_catalog_c]
        list_b = [str(x.resolve()) for x in catalogs_b]
        list_b.sort()
        self.assertListEqual(list_a, list_b)

    #
    # Test database methods
    #
    def test_create_tables(self):
        self.cur.execute("DROP TABLE IF EXISTS catalogs")
        self.cur.execute("DROP TABLE IF EXISTS paths")
        self.lrsync.create_tables()
        self.cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        self.assertListEqual(self.cur.fetchall(), [('catalogs',), ('paths',)])

    def test_select_all_catalogs(self):
        self.cur.execute("DELETE FROM paths")
        self.cur.execute("DELETE FROM catalogs")
        self.lrsync.commit()
        self.cur.execute("INSERT INTO catalogs(catalog_id, catalog_name)"
                         "VALUES (1, 'test_catalog')")
        self.assertListEqual(self.lrsync.select_all_catalogs(), [(1, 'test_catalog', None)])

    def test_select_all_paths(self):
        self.cur.execute("DELETE FROM paths")
        self.cur.execute("DELETE FROM catalogs")
        self.lrsync.commit()
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         "VALUES (1, '/test/path')")
        self.assertListEqual(self.lrsync.select_all_paths(), [(1, '/test/path', 1)])

    def test_select_all_paths_with_catalog_id(self):
        self.cur.execute("DELETE FROM paths")
        self.cur.execute("DELETE FROM catalogs")
        self.lrsync.commit()
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         "VALUES (1, '/test/path/1')")
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         "VALUES (1, '/test/path/2')")
        self.cur.execute("INSERT INTO paths(catalog_id, path)"
                         "VALUES (2, '/test/path/3')")
        self.assertListEqual(self.lrsync.select_all_paths_with_catalog_id(1),
                             [(1, '/test/path/1', 1), (2, '/test/path/2', 1)])
        self.assertListEqual(self.lrsync.select_all_paths_with_catalog_id(2), [(3, '/test/path/3', 2)])

    def test_select_all_paths_for_catalog_name(self):
        self.assertListEqual(self.lrsync.select_all_paths_for_catalog_name(self.test_catalog_a.stem),
                             self.test_paths)

    def test_catalog_id_from_name(self):
        self.cur.execute("INSERT INTO catalogs(catalog_id, catalog_name)"
                         "VALUES (1337, 'test_catalog')")
        result = self.lrsync.catalog_id_from_name("test_catalog")
        self.assertEqual(result, 1337)

        result = self.lrsync.catalog_id_from_name("test_catalog_not_exist")
        self.assertEqual(result, None)

    def test_insert_catalog(self):
        self.lrsync.insert_catalog("test_catalog")
        self.cur.execute("SELECT * FROM catalogs "
                         "WHERE catalog_name = 'test_catalog'")
        self.assertEqual(self.cur.fetchone()[1], "test_catalog")

    def test_delete_catalog(self):
        self.lrsync.delete_catalog(self.test_catalog_a.stem)

        self.cur.execute("SELECT * FROM catalogs")
        catalog_names = [x[1] for x in self.cur.fetchall()]

        self.assertNotIn("test_catalog", catalog_names)

    def test_insert_path(self):
        self.cur.execute("DELETE FROM paths")
        self.cur.execute("DELETE FROM catalogs")
        self.lrsync.commit()

        self.cur.execute("INSERT INTO catalogs(catalog_id, catalog_name)"
                         "VALUES (1337, 'test_catalog')")
        self.lrsync.insert_path("/test/path/to/test_catalog.lrcat", "test_catalog")

        self.cur.execute("SELECT * FROM paths")
        self.assertListEqual(self.cur.fetchall(), [(1, "/test/path/to/test_catalog.lrcat", 1337)])

        self.cur.execute("SELECT path FROM paths WHERE catalog_id = 1337")
        self.assertEqual(self.cur.fetchone()[0], "/test/path/to/test_catalog.lrcat")

    def test_update_last_sync(self):
        ts = time.time()
        self.lrsync.update_last_sync(self.test_catalog_a.stem, ts)
        self.cur.execute(f"SELECT * FROM catalogs WHERE catalog_name = '{self.test_catalog_a.stem}'")

        self.assertEqual(self.cur.fetchone()[2], ts)

    #
    # Test app
    #
    def test_get_catalog_paths(self):
        self.assertListEqual(sorted(self.lrsync.get_catalog_paths(self.test_catalog_a.stem)),
                             sorted([self.test_catalog_a.resolve(),
                                     self.test_catalog_b.resolve()]))

    def test_sync(self):
        self.lrsync.sync(self.test_catalog_a.stem)
        date_a = self.test_catalog_a.stat().st_mtime
        date_b = self.test_catalog_b.stat().st_mtime
        self.assertEqual(date_a, date_b)

        self.lrsync.sync(self.test_catalog_c.stem)
        self.cur.execute(f"SELECT * FROM catalogs WHERE catalog_name = '{self.test_catalog_c.stem}'")
        self.assertIsNotNone(self.cur.fetchone()[2])

    def test_scan(self):
        self.cur.execute("DELETE FROM catalogs")
        self.cur.execute("DELETE FROM paths")
        self.lrsync.commit()

        self.lrsync.scan(Path())
        self.cur.execute("SELECT * FROM catalogs")
        self.assertListEqual(self.cur.fetchall(), self.test_catalogs)

        self.cur.execute("SELECT * FROM paths")

    def test_list_paths(self):
        self.assertEqual(len(self.lrsync.list_paths()), 3)

    def test_list_catalogs(self):
        self.assertEqual(len(self.lrsync.list_catalogs()), 2)

    def test_last_modified_path(self):
        self.assertEqual(self.lrsync.last_modified_path(self.test_catalog_a.stem), self.test_catalog_b.resolve())

    def test_clear(self):
        self.cur.execute("DELETE FROM catalogs")
        self.cur.execute("DELETE FROM paths")
        self.lrsync.commit()

        self.cur.execute("INSERT INTO catalogs(catalog_id, catalog_name)"
                         f"VALUES (1, '{self.test_catalog_name}')")
        self.lrsync.clear()
        self.cur.execute("SELECT * FROM catalogs")
        self.assertListEqual(self.cur.fetchall(), [])

    #
    # Test static methods
    #
    def test_version_from_filename(self):
        self.assertEqual(lightroom_sync.version_from_filename("lr_classic_2020_v001.lrcat"), 1)
        self.assertEqual(lightroom_sync.version_from_filename("lr_v00033_v006.lrcat"), 6)
        self.assertEqual(lightroom_sync.version_from_filename("snelhest_fest_v023.lrcat"), 23)

    def test_filename_to_name_and_version(self):
        self.assertEqual(lightroom_sync.filename_to_name_and_version("lr_classic_2020_v001.lrcat"),
                         ("lr_classic_2020", 1))
        self.assertEqual(lightroom_sync.filename_to_name_and_version("lr_v00033_v006.lrcat"), ("lr_v00033", 6))
        self.assertEqual(lightroom_sync.filename_to_name_and_version("snelhest_fest_v023.lrcat"), ("snelhest_fest", 23))

    def test_mtimes(self):
        file_list = [x for x in self.not_test_catalog.parent.rglob("*") if x.is_file()]
        files_mtimes = {x: y for x, y in lightroom_sync.mtimes(file_list).items()}
        self.assertDictEqual(lightroom_sync.mtimes(file_list), files_mtimes)
