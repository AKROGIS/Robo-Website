# -*- coding: utf-8 -*-
"""
An HTTP server which publishes stats about the robocopy logs database.

Edit the Config object below as needed for each execution.

Works with Python 2.7 and Python 3.x
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from io import open
import json
import os
import sqlite3
import ssl

try:
    # Python 2
    import urlparse
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    # Python 3
    import urllib.urlparse as urlparse
    from http.server import BaseHTTPRequestHandler, HTTPServer


class Config(object):
    """Namespace for configuration parameters. Edit as needed."""

    # pylint: disable=useless-object-inheritance,too-few-public-methods

    # Location of the logs database
    log_database = "E:/XDrive/Logs/logs.db"

    # Secure Service
    # If true creates an https server on port 8443, else it is an http server on port 8080
    # a secure service requires `import ssl`
    secure = True


# pylint: disable=broad-except
# If an unexpected exception occurs, I want to send the error to the user, and continue
# pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-return-statements
# I know this code is a little complicated, but I'm not going to risk refactoring.
# pylint: disable=invalid-name,no-self-use
# issues cannot be corrected without breaking the class contract.


class SyncHandler(BaseHTTPRequestHandler):
    """A simple HTTP server."""

    db_name = Config.log_database
    name = "XDrive RoboCopy Log Details"
    usage = """
        Usage:
            GET with /summary or summary?date=YYYY-MM-DD to get the log summary
            GET with /parks or parks?date=YYYY-MM-DD to get the log details for all parks
            GET with /plot1 or plot1?date=YYYY-MM-DD to get data for a speed comparison of all parks
            GET with /dates to get the min and max date of the logs in the database
            GET with /help for this message
    """

    def do_GET(self):
        """Handle a GET request."""
        path_parts = urlparse.urlparse(self.path)
        params = urlparse.parse_qs(path_parts.query)
        sql_params = []
        if path_parts.path == "/summary":
            sql = """
                SELECT l.date AS summary_date,
                COUNT(*) AS count_start,
                COUNT(l1.park) AS count_unfinished,
                COUNT(e1.log_id) AS count_with_errors,
                CASE WHEN c.date IS NULL THEN 0 ELSE 1 END AS has_changes,
                CASE WHEN e2.date IS NULL THEN 0 ELSE 1 END AS has_parse_errors
                FROM logs AS l
                LEFT JOIN logs AS l1 ON l.log_id = l1.log_id and (l1.finished = 0 OR l1.finished IS NULL)
                LEFT JOIN (SELECT log_id FROM errors WHERE failed GROUP BY log_id) AS e1 ON l.log_id = e1.log_id
                LEFT JOIN changes AS c on l.date = c.date
                LEFT JOIN (SELECT SUBSTR(DATETIME(TimeStamp, '-1 day'), 0 ,11) as date from log group by date) as e2 ON l.date = e2.date
                WHERE l.date = (SELECT MAX(date) FROM logs)
                GROUP BY l.date;
            """
            if "date" in params and len(params["date"]) == 1:
                date = params["date"][0]
                date = self.sanitize_date(date)
                if date:
                    sql = sql.replace(
                        "WHERE l.date = (SELECT MAX(date) FROM logs)",
                        "WHERE l.date = ?",
                    )
                    sql_params = [date]
                else:
                    self.err_response("Bad date request")
                    return
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_one(database, sql, sql_params)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/parks":
            sql = """
                SELECT l.park, l.date, l.finished,
                COALESCE(e.count_errors, 0) AS count_errors,
                sf.copied AS files_copied, sf.extra AS files_removed, sf.total AS files_scanned,
                st.copied AS time_copying, st.extra AS time_scanning, sb.copied AS bytes_copied
                FROM logs AS l
                LEFT JOIN stats AS sf ON l.log_id = sf.log_id and sf.stat = 'files'
                LEFT JOIN stats AS st ON l.log_id = st.log_id and st.stat = 'times'
                LEFT JOIN stats AS sb ON l.log_id = sb.log_id and sb.stat = 'bytes'
                LEFT JOIN (select log_id, COUNT(*) AS count_errors FROM errors where failed group by log_id) AS e ON l.log_id = e.log_id
                WHERE l.date = (SELECT MAX(date) FROM logs)
                ORDER BY l.park;
            """
            if "date" in params and len(params["date"]) == 1:
                date = params["date"][0]
                date = self.sanitize_date(date)
                if date:
                    sql = sql.replace(
                        "WHERE l.date = (SELECT MAX(date) FROM logs)",
                        "WHERE l.date = ?",
                    )
                    sql_params = [date]
                else:
                    self.err_response("Bad date request")
                    return
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/error_summary":
            sql = """
                SELECT e.error_code, c.error_name, count(*) AS count
                FROM errors AS e JOIN error_codes AS c
                ON e.error_code = c.error_code
                WHERE e.failed AND log_id = ?
                ORDER BY e.error_code;
            """
            # Return nothing (log_id = 0), instead of an error when given bad input
            log_id = 0
            if "log" in params and len(params["log"]) == 1:
                log_text = params["log"][0]
                try:
                    log_id = int(log_text)
                except ValueError:
                    pass
            sql_params = [log_id]
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/error_details":
            sql = """
                SELECT REPLACE(message,'E:\\XDrive\\RemoteServers\\XDrive-','') AS message
                FROM errors
                WHERE log_id = ? AND error_code = ? ORDER BY error_id;
            """
            # Return nothing (log_id = 0), instead of an error when given bad input
            log_id = 0
            code = 0
            if "log" in params and len(params["log"]) == 1:
                log_text = params["log"][0]
                try:
                    log_id = int(log_text)
                except ValueError:
                    pass
            if "code" in params and len(params["code"]) == 1:
                code_text = params["code"][0]
                try:
                    code = int(code_text)
                except ValueError:
                    pass
            sql_params = [log_id, code]
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/logfile":
            sql = "SELECT filename FROM logs WHERE date = ? AND park = ?"
            date = None
            if "date" in params and len(params["date"]) == 1:
                date = params["date"][0]
                date = self.sanitize_date(date)
            park = None
            if "park" in params and len(params["park"]) == 1:
                park = params["park"][0]
            filename = None
            if park and date:
                sql_params = [date, park]
                with sqlite3.connect(self.db_name) as database:
                    try:
                        resp = self.db_get_one(database, sql, sql_params)
                        if resp and "filename" in resp:
                            filename = resp["filename"]
                    except Exception as ex:
                        self.err_response("{0}".format(ex))
                        return
            if filename:
                filename = os.path.basename(filename)
                folder = os.path.dirname(Config.log_database)
                archive = date[:4] + "archive"
                filename = os.path.join(folder, archive, filename)
                if os.path.exists(filename):
                    self.file_response(filename)
                else:
                    msg = "log file {0} not found".format(filename)
                    self.err_response(msg)
            else:
                folder = os.path.dirname(Config.log_database)
                filename = os.path.join(folder, "LogProcessor.log")
                if os.path.exists(filename):
                    self.file_response(filename)
                else:
                    msg = "log file {0} not found".format(filename)
                    self.err_response(msg)

        elif path_parts.path == "/dates":
            sql = """
                SELECT
                MIN(date) as first_date,
                MAX(date) as last_date
                FROM logs;
            """
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_one(database, sql)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/plot1":
            sql = """
                SELECT l.park,
                COALESCE(round(1.0*sf.total/st.extra, 1), 0) AS scan_speed,
                COALESCE(round(sb.copied/st.copied/1000.0, 1), 0) AS copy_speed
                FROM logs AS l
                LEFT JOIN stats AS sf ON l.log_id = sf.log_id and sf.stat = 'files'
                LEFT JOIN stats AS st ON l.log_id = st.log_id and st.stat = 'times'
                LEFT JOIN stats AS sb ON l.log_id = sb.log_id and sb.stat = 'bytes'
                WHERE l.date = (SELECT MAX(date) FROM logs)
                ORDER BY l.park;
            """
            if "date" in params and len(params["date"]) == 1:
                date = params["date"][0]
                date = self.sanitize_date(date)
                if date:
                    sql = sql.replace(
                        "WHERE l.date = (SELECT MAX(date) FROM logs)",
                        "WHERE l.date = ?",
                    )
                    sql_params = [date]
                else:
                    self.err_response("Bad date request")
                    return
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params, False)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/scanavg":
            sql = """
                SELECT l.park,
                ROUND(AVG(1.0*sf.total/st.extra), 1) AS avg_scan_speed,
                COUNT(*) AS CNT
                FROM logs AS l
                LEFT JOIN stats AS sf ON l.log_id = sf.log_id and sf.stat = 'files'
                LEFT JOIN stats AS st ON l.log_id = st.log_id and st.stat = 'times'
                LEFT JOIN errors AS e ON l.log_id = e.log_id
                WHERE e.log_id IS NULL
                AND st.extra > 0 AND sf.total > 0
                AND l.date > ?
                AND l.date < ?
                GROUP BY l.park
                ORDER BY l.park;
            """
            if "start" in params and len(params["start"]) == 1:
                date = params["start"][0]
                date = self.sanitize_date(date)
                if date:
                    sql_params.append(date)
                else:
                    self.err_response("Bad start date parameter")
                    return
            else:
                sql = sql.replace("AND l.date > ?", "")
            if "end" in params and len(params["end"]) == 1:
                date = params["end"][0]
                date = self.sanitize_date(date)
                if date:
                    sql_params.append(date)
                else:
                    self.err_response("Bad end date parameter")
                    return
            else:
                sql = sql.replace("AND l.date < ?", "")
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params, False)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/copyavg":
            sql = """
                SELECT l.park,
                ROUND(AVG(1.0*sb.copied/st.copied/1000.0), 1) AS avg_copy_speed,
                COUNT(*) AS CNT
                FROM logs AS l
                LEFT JOIN stats AS st ON l.log_id = st.log_id and st.stat = 'times'
                LEFT JOIN stats AS sb ON l.log_id = sb.log_id and sb.stat = 'bytes'
                LEFT JOIN errors AS e ON l.log_id = e.log_id
                WHERE e.log_id IS NULL
                AND st.copied > 0 AND sb.copied > 0
                AND l.date > ?
                AND l.date < ?
                GROUP BY l.park
                ORDER BY l.park;
            """
            if "start" in params and len(params["start"]) == 1:
                date = params["start"][0]
                date = self.sanitize_date(date)
                if date:
                    sql_params.append(date)
                else:
                    self.err_response("Bad start date parameter")
                    return
            else:
                sql = sql.replace("AND l.date > ?", "")
            if "end" in params and len(params["end"]) == 1:
                date = params["end"][0]
                date = self.sanitize_date(date)
                if date:
                    sql_params.append(date)
                else:
                    self.err_response("Bad end date parameter")
                    return
            else:
                sql = sql.replace("AND l.date < ?", "")
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params, False)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/speed":
            sql = """
                SELECT l.park, l.date,
                ROUND(1.0*sf.total/st.extra, 1) AS scan_speed,
                ROUND(1.0*sb.copied/st.copied/1000.0, 1) AS copy_speed,
                ROUND(1.0*sb.copied/sf.copied/1000.0, 1) AS avg_size_kb,
                sf.copied as files,
                ROUND(sb.copied/1000.0/1000.0, 2) as MBytes
                FROM logs AS l
                LEFT JOIN stats AS sf ON l.log_id = sf.log_id and sf.stat = 'files'
                LEFT JOIN stats AS st ON l.log_id = st.log_id and st.stat = 'times'
                LEFT JOIN stats AS sb ON l.log_id = sb.log_id and sb.stat = 'bytes'
                LEFT JOIN errors AS e ON l.log_id = e.log_id
                WHERE e.log_id IS NULL
                AND l.date > ?
                AND l.date < ?
                AND l.park = ?
                ORDER BY l.park, l.date;
            """
            if "start" in params and len(params["start"]) == 1:
                date = params["start"][0]
                date = self.sanitize_date(date)
                if date:
                    sql_params.append(date)
                else:
                    self.err_response("Bad start date parameter")
                    return
            else:
                sql = sql.replace("AND l.date > ?", "")
            if "end" in params and len(params["end"]) == 1:
                date = params["end"][0]
                date = self.sanitize_date(date)
                if date:
                    sql_params.append(date)
                else:
                    self.err_response("Bad end date parameter")
                    return
            else:
                sql = sql.replace("AND l.date < ?", "")
            if "park" in params and len(params["park"]) == 1:
                park = params["park"][0]
                park = self.sanitize_park(park)
                if park:
                    sql_params.append(park)
                else:
                    self.err_response("Bad park parameter")
                    return
            else:
                sql = sql.replace("AND l.park = ?", "")
            with sqlite3.connect(self.db_name) as database:
                try:
                    resp = self.db_get_rows(database, sql, sql_params, False)
                    self.std_response(resp)
                except Exception as ex:
                    self.err_response("{0}".format(ex))

        elif path_parts.path == "/help":
            self.std_response({"help": self.usage})
        else:
            self.err_response(self.usage)

    def std_response(self, obj):
        """respond with a JSON (obj) object."""

        data = json.dumps(obj)
        # Python 2 with no unicode text in JSON object will return a byte string
        # otherwise data will be unicode which needs to be encoded to bytes
        try:
            data = data.encode("utf8")
        except AttributeError:
            pass
        self.send_response(200)
        self.send_header("Content-type", "json")
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def file_response(self, filename):
        """Respond with the contents of filename."""

        try:
            in_file = open(filename, "rb")
            self.send_response(200)
            self.send_header("Content-type", "text")
            self.end_headers()
            self.wfile.write(in_file.read())
            in_file.close()
        except IOError:
            self.send_error(404, "File Not Found: {0}".format(filename))

    def err_response(self, message):
        """Respond with an error message."""

        data = json.dumps({"error": message}).encode("utf8")
        self.send_response(500)
        self.send_header("Content-type", "json")
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        """Handle a POST request."""

        if self.path == "/sync":
            self.err_response("not implemented")

    def end_headers(self):
        """Send the end of a header."""

        self.send_header("Access-Control-Allow-Origin", "*")
        BaseHTTPRequestHandler.end_headers(self)

    def db_get_rows(self, database, sql, params, header=True):
        """Execute sql on the database and return the resulting rows."""

        cursor = database.cursor()
        rows = cursor.execute(sql, params).fetchall()
        if header:
            return [[item[0] for item in cursor.description]] + rows
        return rows

    def db_get_one(self, database, sql, params=None):
        """Execute sql on the database and return the resulting row."""

        if params is None:
            params = []
        cursor = database.cursor()
        row = cursor.execute(sql, params).fetchone()
        header = [item[0] for item in cursor.description]
        # types = [item[1] for item in cursor.description]
        results = {}
        if row:
            for i, item in enumerate(row):
                results[header[i]] = item
        return results

    def sanitize_date(self, text):
        """Return text or None if text is not a valid date in the YYYY-MM-DD format."""

        try:
            date = datetime.datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return None
        return date.strftime("%Y-%m-%d")

    def sanitize_park(self, text):
        """Return one of parks or None if text (case insensitive) is not in parks."""

        parks = [
            "DENA",
            "GLBA",
            "KATM",
            "KEFJ",
            "KENN",
            "KLGO",
            "KOTZ",
            "LACL",
            "NOME",
            "SEAN",
            "SITK",
            "WRST",
            "YUGA",
        ]
        try:
            park = text.upper()
            if park not in parks:
                return None
        except ValueError:
            return None
        return park


if Config.secure:
    # For more info on https see: https://gist.github.com/dergachev/7028596
    server = HTTPServer(("", 8443), SyncHandler)
    server.socket = ssl.wrap_socket(
        server.socket, keyfile="key.pem", certfile="cert.pem", server_side=True
    )
else:
    server = HTTPServer(("", 8080), SyncHandler)

server.serve_forever()
