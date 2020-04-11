#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
lightroom_sync.py
Lightroom sync is a script to synchronize your lightroom catalogs across multiple devices.
"""
import click
import os
import sqlite3
import re
import logging
import shutil
import time
from logging.config import dictConfig
from pathlib import Path


def setup_logging(level="debug"):
    if level == "info":
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    logging_config = dict(
        version=1,
        formatters={
            "f": {"format": "%(asctime)s %(name)-6s %(funcName)-16s %(levelname)-8s %(message)s"}
        },
        handlers={
            "sh": {"class": "logging.StreamHandler",
                   "formatter": "f",
                   "level": log_level},
            "fh": {"class": "logging.FileHandler",
                   "formatter": "f",
                   "filename": "lrsync.log",
                   "level": log_level}
        },
        root={
            "handlers": ["sh", "fh"],
            "level": log_level,
        },
    )

    dictConfig(logging_config)

    logger = logging.getLogger()
    return logger


setup_logging(level="debug")


class LightroomSync:
    def __init__(self, db_name="lrsync.db"):
        self.db = db_name
        self.conn = sqlite3.connect(self.db)
        self.cur = self.conn.cursor()
        self.create_tables()

    def sync(self, catalog_name=None, backup=True):
        """Sync all or just one catalog across the paths found in the database"""
        if catalog_name is not None:
            # Get all paths for catalog
            paths = self.get_catalog_paths(catalog_name)
            # Get latest modified path
            last_modified = self.last_modified_path(catalog_name)
            logging.debug(f"Last modified file was {last_modified}")

            # Copy latest to the other paths
            for path in paths:
                if path.resolve() != last_modified.resolve():
                    shutil.copy2(str(last_modified.resolve()), str(path.resolve()))
                    logging.debug(f"Copied catalog from {last_modified.resolve()} to {path.resolve()}")
            # Update last sync date in database
            self.update_last_sync(catalog_name, time.time())
            return True

    def scan(self, directory):
        """Scan a directory and add all Lightroom catalogs to database"""
        print(f"Scanning {directory} for Lightroom catalogs")
        # Get list of catalog paths
        catalogs = scan_for_catalogs(directory)
        logging.debug(f"Found {len(catalogs)} catalogs in {directory}")

        for catalog in catalogs:
            logging.debug(f"Processing {catalog}")
            path = str(catalog.resolve())
            name = str(catalog.stem)
            logging.debug(f"{name, path}")

            self.insert_catalog(name)
            logging.debug(f"Added catalog {name} to database")

            self.insert_path(path, name)
            logging.debug(f"Added path {path} to database and linking to catalog {name}")

        print(f"Found {len(catalogs)} Lightroom catalogs")

    def clear(self):
        """Clear out the database"""
        self.execute("DELETE FROM catalogs")
        self.execute("DELETE FROM paths")
        self.commit()
        return True

    def list_catalogs(self):
        """List all paths in the database"""
        paths = self.select_all_paths()
        catalogs = []
        for c in self.select_all_catalogs():
            catalogs.append({
                "id": c[0],
                "name": c[1],
                "paths": len([x for x in paths if x[2] == c[0]]),
                "last_sync": c[2]
            })

        # Setup formatting
        len_id = len("ID") + 2
        if catalogs:
            len_name = len(max([catalogs[x]["name"] for x in range(len(catalogs))], key=len)) + 2
        else:
            len_name = 8

        len_paths = len("Paths") + 2
        len_last_sync = len("Last sync") + 2
        if catalogs:
            longets_sync_date = [catalogs[x]["last_sync"] for x in range(len(catalogs))
                                 if not catalogs[x]["last_sync"] is None]
            if longets_sync_date:
                len_last_sync = len(max(longets_sync_date, key=len)) + 2

        print("ID".ljust(len_id),
              "Name".ljust(len_name),
              "Paths".ljust(len_paths),
              "Last sync".ljust(len_last_sync))
        print("".ljust(len_id + len_name + len_paths + len_last_sync + 1, "-"))
        for catalog in catalogs:
            print(str(catalog['id']).ljust(len_id),
                  str(catalog['name']).ljust(len_name),
                  str(catalog['paths']).ljust(len_paths),
                  str(catalog['last_sync']).ljust(len_last_sync))

        return catalogs

    def list_paths(self):
        """List all paths in the database"""
        catalogs = self.select_all_catalogs()
        paths = []
        for p in self.select_all_paths():
            paths.append({
                "id": p[0],
                "path": p[1],
                "cat_id": p[2],
                "cat_name": [x[1] for x in catalogs if x[0] == p[2]][0]
            })

        # Setup formatting
        len_id = len("ID") + 2
        if paths:
            len_path = len(max([paths[x]["path"] for x in range(len(paths))], key=len)) + 2
        else:
            len_path = 8
        len_cat_id = len("Cat. ID") + 2
        if paths:
            len_cat_name = len(max([paths[x]["cat_name"] for x in range(len(paths))], key=len)) + 2
        else:
            len_cat_name = len("Cat. Name") + 2

        print("ID".ljust(len_id),
              "Path".ljust(len_path),
              "Cat. ID".ljust(len_cat_id),
              "Cat. Name".ljust(len_cat_name))
        print("".ljust(len_id + len_path + len_cat_id + len_cat_name, "-"))
        for path in paths:
            print(str(path['id']).ljust(len_id),
                  str(path['path']).ljust(len_path),
                  str(path['cat_id']).ljust(len_cat_id),
                  str(path['cat_name']).ljust(len_cat_name))

        return paths

    def last_modified_path(self, catalog_name):
        """Get the last modified file for a catalog"""
        cat_id = self.catalog_id_from_name(catalog_name)

        paths = [x[1] for x in self.select_all_paths_with_catalog_id(cat_id)]
        paths_with_mtimes = mtimes(paths)
        latest = max(paths_with_mtimes, key=paths_with_mtimes.get)
        latest_path = Path(latest)
        return latest_path

    def get_catalog_paths(self, catalog):
        """Get all paths for a catalog name or id"""
        if isinstance(catalog, str):
            result = self.select_all_paths_for_catalog_name(catalog)
        elif isinstance(catalog, int):
            result = self.select_all_paths_with_catalog_id(catalog)
        paths = [Path(x[1]) for x in result]
        logging.debug(paths)
        return paths

    # Database actions
    def commit(self):
        self.conn.commit()

    def execute(self, query):
        self.cur.execute(query)

    def close(self):
        self.conn.close()

    #
    # Database related
    #
    def create_tables(self):
        """Create the tables to be used"""
        self.execute(""" -- Create catalogs table
                    CREATE TABLE IF NOT EXISTS catalogs(
                        catalog_id INTEGER PRIMARY KEY,
                        catalog_name TEXT NOT NULL UNIQUE,
                        last_sync INTEGER
                    );
                    """)
        self.execute("""
                    -- Create paths table
                    CREATE TABLE IF NOT EXISTS paths(
                        path_id INTEGER PRIMARY KEY,
                        path text UNIQUE,
                        catalog_id INTEGER,
                        FOREIGN KEY(catalog_id) REFERENCES catalogs(catalog_id)
                    );
                """)
        self.commit()
        return True

    def select_all_catalogs(self):
        """Return all content from a table"""
        self.execute(f"SELECT * FROM catalogs")
        return self.cur.fetchall()

    def select_all_paths(self):
        """Return all content from a table"""
        self.execute(f"SELECT * FROM paths")
        return self.cur.fetchall()

    def select_all_paths_with_catalog_id(self, catalog_id):
        """Return all content from a table"""
        self.execute("SELECT * FROM paths "
                     f"WHERE catalog_id = {catalog_id}")
        return self.cur.fetchall()

    def select_all_paths_for_catalog_name(self, catalog_name):
        """Return all content from a table"""
        self.execute("SELECT * FROM paths "
                     f"WHERE catalog_id = (SELECT catalog_id FROM catalogs WHERE catalog_name = '{catalog_name}');")
        return self.cur.fetchall()

    def catalog_id_from_name(self, catalog_name):
        self.execute("SELECT catalog_id FROM catalogs "
                     f"WHERE catalog_name = '{catalog_name}';")
        ids = self.cur.fetchone()
        if ids:
            return ids[0]
        else:
            return None

    def insert_catalog(self, catalog_name):
        """Insert a catalog into the database"""
        self.execute("INSERT INTO catalogs(catalog_name) "
                     f"SELECT '{catalog_name}' "
                     f"WHERE NOT EXISTS (SELECT * FROM catalogs WHERE catalog_name = '{catalog_name}');")
        self.commit()
        return True

    def delete_catalog(self, catalog_name):
        """Delete a catalog from the database"""
        self.execute(f"DELETE FROM catalogs WHERE catalog_name = '{catalog_name}'")
        self.commit()
        return True

    def insert_path(self, path, catalog_name):
        """Insert a path and link to a catalog"""
        cat_id = self.catalog_id_from_name(catalog_name)
        self.execute("INSERT INTO paths(path, catalog_id) "
                     f"SELECT '{path}', {cat_id} "
                     "WHERE NOT EXISTS (SELECT * FROM paths "
                     f"WHERE path = '{path}');")
        self.commit()
        return True

    def update_last_sync(self, catalog_name, timestamp):
        self.execute("UPDATE catalogs "
                     f"SET last_sync = {timestamp} "
                     f"WHERE catalog_name = '{catalog_name}';")
        self.commit()

        return True


def mtimes(file_list):
    """Return a list of modified times for the given list of files"""
    files = {}
    for f in file_list:
        path = Path(f)
        files[f] = path.stat().st_mtime
    return files


def scan_for_catalogs(directory):
    """Scan a directory for catalog files"""
    catalogs = []
    path = Path(directory)

    # Walk through files and directories
    for root, dirs, files in os.walk(path, topdown=True):
        # Skip lrdata folders
        dirs[:] = [x for x in dirs if not x.endswith(".lrdata")]
        # Skip backups folders
        dirs[:] = [x for x in dirs if "backups" not in x]

        # Get catalog files
        catalogs.extend([Path(root) / f for f in files if Path(f).suffix == ".lrcat"])

    return catalogs


def is_version_string(input_string):
    """Check if a string is a version string according to a regex"""
    if re.match(r"^v(\d\d\d)$", input_string):
        return True
    return False


def version_from_filename(filename):
    """Extract a version number from a filename"""
    name = Path(filename).stem
    for i in name.split("_"):
        if is_version_string(i):
            return int(i[1:])
    return False


def filename_to_name_and_version(filename):
    """Split up a versioned filename into name and version"""
    path = Path(filename).stem
    name = "_".join([x for x in path.split("_") if not is_version_string(x)])
    version = version_from_filename(filename)
    return name, version


#
# CLI
#
@click.group()
def cli():
    pass


@cli.command()
@click.argument("catalog", default=None)
def sync(catalog):
    """Sync """
    lrsync = LightroomSync()
    lrsync.sync(catalog)


@cli.command()
@click.argument("directory", default=Path())
def scan(directory):
    """Scan the directory for Lightroom catalogs"""
    lrsync = LightroomSync()
    lrsync.scan(directory)


@cli.command()
def clear():
    """Clear the database. WARNING: This deletes all records"""
    print("Are you sure you want to clear the entire database? This can't be undone\n")

    print("Enter CLEAR to continue or press any other key to cancel:")
    response = input("> ")
    if response == "CLEAR":
        lrsync = LightroomSync()
        lrsync.clear()
    else:
        print("Nothing was modified")


@cli.command()
@click.option("--catalogs/--paths", default=True)
def list(catalogs):
    """List all the catalogs or paths in the database"""
    lrsync = LightroomSync()
    if catalogs:
        lrsync.list_catalogs()
    else:
        lrsync.list_paths()


if __name__ == '__main__':
    cli()
