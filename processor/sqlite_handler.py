# -*- coding: utf-8 -*-
"""
A minimal SQLite handler for the python logging module

from: https://gist.github.com/giumas/994e48d3c1cff45fbe93
with minor changes

Edit the Config object below as needed for each execution.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sqlite3
import time


class Config(object):
    """Namespace for configuration parameters. Edit as needed."""

    # pylint: disable=useless-object-inheritance,too-few-public-methods

    # SQL command to initialize the database for logging
    initial_sql = """
        CREATE TABLE IF NOT EXISTS log(
            TimeStamp TEXT,
            Source TEXT,
            LogLevel INT,
            LogLevelName TEXT,
            Message TEXT,
            Module TEXT,
            FuncName TEXT,
            LineNo INT,
            Exception TEXT,
            Process INT,
            Thread TEXT,
            ThreadName TEXT
        )
    """
    # SQL Command to insert a log record.
    insertion_sql = """
        INSERT INTO log(
            TimeStamp,
            Source,
            LogLevel,
            LogLevelName,
            Message,
            Module,
            FuncName,
            LineNo,
            Exception,
            Process,
            Thread,
            ThreadName
        )
        VALUES (
            '%(dbtime)s',
            '%(name)s',
            %(levelno)d,
            '%(levelname)s',
            '%(message)s',
            '%(module)s',
            '%(funcName)s',
            %(lineno)d,
            '%(exc_text)s',
            %(process)d,
            '%(thread)s',
            '%(threadName)s'
        );
    """


class SQLiteHandler(logging.Handler):
    """Thread-safe logging handler for SQLite."""

    # issues cannot be corrected without breaking the class contract.
    # pylint: disable=invalid-name,no-self-use,protected-access

    def __init__(self, db="app.db"):
        logging.Handler.__init__(self)
        self.db = db
        conn = sqlite3.connect(self.db)
        conn.execute(Config.initial_sql)
        conn.commit()

    def format_time(self, record):
        """Create a time stamp."""

        record.dbtime = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(record.created)
        )

    def format_msg(self, record):
        """Remove single quotes from message."""

        record.message = record.message.replace("'", '"')

    def emit(self, record):
        """Send a log record to the database."""

        self.format(record)
        self.format_time(record)
        self.format_msg(record)
        if record.exc_info:  # for exceptions
            record.exc_text = logging._defaultFormatter.formatException(record.exc_info)
            record.exc_text = record.exc_text.replace("'", '"')
        else:
            record.exc_text = ""

        # Insert the log record
        sql = Config.insertion_sql % record.__dict__
        conn = sqlite3.connect(self.db)
        conn.execute(sql)
        conn.commit()  # not efficient, but hopefully thread-safe
