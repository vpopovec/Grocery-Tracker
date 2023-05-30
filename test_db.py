import pytest
import sqlite3
from db import Database


def test_get_db_conn():
    db = Database()
    assert db.conn is Database().conn
