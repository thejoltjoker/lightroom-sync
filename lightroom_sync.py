#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
lightroom_sync.py
Lightroom sync is a script to synchronize your lightroom catalogs across multiple devices.
"""
import argparse
import sqlite3
from pathlib import Path


class LightroomSync:
    def __init__(self):
        pass

    def scan_for_catalogs(self, directory):
        pass

    def version_up(self, catalog):
        """Increment the latest version of a catalog"""
        pass


class Database:
    def __init__(self, db_name="lrsync.db"):
        self.db = db_name
        self.conn = self.connect()
        self.cursor = self.conn.cursor()

    def connect(self):
        return sqlite3.connect(self.db)

    def create_tables(self):
        self.cursor.execute("INSERT TABLE catalogs IF NOT EXIST;")
    # def add_catalog(self, catalog_name, ):
    #     self.cursor.execute(f"INSERT {}")


def main():
    """docstring for main"""
    pass


if __name__ == '__main__':
    main()
