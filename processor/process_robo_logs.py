# -*- coding: utf-8 -*-
"""
Reads the log files from robocopy and summarizes them in a database
Emails an admin when issues are found in the log file.

Edit the Config object below as needed for each execution.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from io import open
import glob
import logging
import logging.config
import os
import sqlite3
import time

import config_logger


class Config(object):
    """Namespace for configuration parameters. Edit as needed."""

    # pylint: disable=useless-object-inheritance,too-few-public-methods

    # Folder where the log files live
    log_folder = r"E:\XDrive\Logs"

    # Path to the sqlite3 database with the log data
    database_path = os.path.join(log_folder, "logs.db")

    # Path to the "PDS Change Log" - describes changes robocopy is propagating
    change_log_path = r"\\inpakrovmdist\gisdata2\GIS\ThemeMgr\PDS_ChangeLog.txt"


# Configure and start the logger
logging.config.dictConfig(config_logger.config)
# Comment the next line during testing, uncomment in production
logging.raiseExceptions = False  # Ignore errors in the logging system
logger = logging.getLogger("main")
logger.info("Logging Started")


# pylint: disable=broad-except
# If an unexpected exception occurs, I want to log the error, and continue
# pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
# I know this code is a little complicated, but I'm not going to risk refactoring.


def process_summary(file_handle, filename, line_num):
    """Return a records of stats for the summary section of the log file."""

    results = {}
    for key, text in [
        ("dirs", "Dirs :"),
        ("files", "Files :"),
        ("bytes", "Bytes :"),
        ("times", "Times :"),
    ]:
        try:
            line = file_handle.next()
            line_num += 1
            results[key] = process_summary_line(line, text, filename, line_num)
        except Exception as ex:
            logger.error(
                (
                    "Unexpected exception processing summary, "
                    "file: %s, line#: %d, key: %s, text: %s, line: %s, exception: %s"
                ),
                filename,
                line_num,
                key,
                text,
                line,
                ex,
            )
    return results, line_num


def process_summary_line(line, sentinel, filename, line_num):
    """Return a records of stats for a line in the summary section of the log file."""

    count_obj = {}
    count_obj["total"] = -1
    count_obj["copied"] = -1
    count_obj["skipped"] = -1
    count_obj["mismatch"] = -1
    count_obj["failed"] = -1
    count_obj["extra"] = -1

    if sentinel not in line:
        logger.error(
            'Summary for "%s" is missing in line: %s, file: %s, line#: %d',
            sentinel,
            line,
            filename,
            line_num,
        )
        return count_obj

    try:
        clean_line = line.replace(sentinel, "")
        if sentinel == "Bytes :":
            counts = [
                int(float(item))
                for item in clean_line.replace(" t", "e12")
                .replace(" g", "e9")
                .replace(" m", "e6")
                .replace(" k", "e3")
                .split()
            ]
        elif sentinel == "Times :":
            clean_line = clean_line.replace("          ", "   0:00:00")
            times = [time.strptime(item, "%H:%M:%S") for item in clean_line.split()]
            counts = [t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec for t in times]
        else:
            counts = [int(item) for item in clean_line.split()]

        count_obj["total"] = counts[0]
        count_obj["copied"] = counts[1]
        count_obj["skipped"] = counts[2]
        count_obj["mismatch"] = counts[3]
        count_obj["failed"] = counts[4]
        count_obj["extra"] = counts[5]
    except Exception as ex:
        logger.error(
            "Parsing summary for %s in line: %s, file: %s, line#: %d, exception: %s",
            sentinel,
            line,
            filename,
            line_num,
            ex,
        )

    return count_obj


def process_error(file_handle, filename, line, line_num, error_sentinel):
    """Return information about a error in the log file."""

    code, message = parse_error_line(line, filename, line_num, error_sentinel)
    error_line_num = line_num
    if not code:
        logger.error(
            "Unable to get the error code from an error line, file: %s, line#: %d, line: %s",
            filename,
            line_num,
            line,
        )
    name = "Name of error not defined"
    retry = False
    eof = False
    try:
        # next line is the name of the error (always valid in 1 year of log data)
        # The name line ends with 0x0D0D0A (\r\r\n), which python (win and mac)
        # interprets as one line. vscode interprets as 2 lines (for line counting),
        # but notepad and other editors do not. we will not double count this line,
        # so line numbers will NOT match vscode line numbers.
        name = file_handle.next().strip()
        line_num += 1
        # From known log files: next lines will be one of a) retry, b) blank, or c) error (EOF)
        #   EOF occurs if robocopy is killed while recovering/waiting for an error
        #   for example, see 2018-11-07_22-00-02-KLGO-update-x-drive.log
        # Use try/except to catch StopIteration exception (EOF)
        try:
            line = file_handle.next()
            line_num += 1
        except StopIteration:
            eof = True
            line = ""
        clean_line = line.strip()
        if clean_line.endswith("... Retrying..."):
            retry = True
        elif clean_line:
            # Not blank or Retry
            # log as an error an treat as a blank line (throw this line away)
            logger.error(
                "Unexpected data on retry line after error in log file: %s, line#: %d, line: %s",
                filename,
                line_num,
                line,
            )
    except Exception as ex:
        logger.error(
            (
                "Unexpected exception processing error lines in log "
                "file: %s, line#: %d, line: %s, exception: %s"
            ),
            filename,
            line_num,
            line,
            ex,
        )

    # Error has failed unless we get a retry message
    error = {
        "code": code,
        "failed": not retry,
        "name": name,
        "line_num": error_line_num,
        "message": message,
    }
    # ignore the last line read (blank or retry), caller can read the next line to continue
    return (error, eof, retry, line_num)


def parse_error_line(line, filename, line_num, error_sentinel):
    """Return information about one line in a error section of the log file."""

    code = 0
    message = "Message not defined"
    try:
        code = int(line.split(error_sentinel)[1].split()[0])
        message = line.split(") ")[1].strip()
    except Exception as ex:
        logger.error(
            "Parsing error line in log file: %s, line#: %d, line: %s, exception: %s",
            filename,
            line_num,
            line,
            ex,
        )
    return code, message


def process_park(file_name):
    """Return statistics for a single log file (each park is logged separately)."""

    summary_header = "Total    Copied   Skipped  Mismatch    FAILED    Extras"
    error_sentinel = " ERROR "
    finished_sentinel = "   Ended : "
    paused_sentinel = "    Hours : Paused at 06:"

    results = {}
    basename = os.path.basename(file_name)
    park = basename[20:24]
    date = basename[:10]
    results["park"] = park
    results["date"] = date
    results["filename"] = file_name
    results["finished"] = None
    results["errors"] = []
    line_num = 0
    error_line_num = line_num
    saved_error = {}  # used when we are retrying an error.
    with open(file_name, "r", encoding="utf-8") as file_handle:
        for line in file_handle:
            try:
                line_num += 1
                if error_sentinel in line:
                    error, eof, retry, line_num = process_error(
                        file_handle, file_name, line, line_num, error_sentinel
                    )
                    if saved_error and saved_error["message"] != error["message"]:
                        saved_error["failed"] = True
                        results["errors"].append(saved_error)
                        saved_error = {}
                    if eof:
                        # Nothing comes next
                        results["errors"].append(error)
                        break
                    if not retry:
                        # We don't care what comes next, we will treat it all the
                        # same. This includes the failing after the last retry
                        # (next line will be RETRY LIMIT EXCEEDED)
                        # this will only be non null when
                        #   saved_error['message'] == error['message']
                        saved_error = {}
                        results["errors"].append(error)
                    else:  # error is retrying
                        # if not saved_error then saved_error['message'] == error['message'],
                        # so assignment is redundant but harmless
                        saved_error = error
                        error_line_num = line_num
                        # Options for what comes next:
                        #   1) same error repeats as a fail: clear saved_error,
                        #      log new error, continue
                        #   2) same error repeats with a new retry: (re)set
                        #      saved_error, continue
                        #   3) new error: save saved_error as fail, process new
                        #      error based on retry status
                        #   4) retry succeeds: log this error: status should be non-fail
                    continue
                if saved_error:
                    # this line is not an error and the last error we saw was retrying
                    #   1) this is a repeat of the file name before the error,
                    #      which means nothing, need to check following line
                    #   2) this is a new filename
                    retry_worked = line_num - error_line_num > 1
                    if retry_worked:
                        results["errors"].append(
                            saved_error
                        )  # logs a non-failing error
                        saved_error = {}
                if line.strip() == summary_header:
                    summary, line_num = process_summary(
                        file_handle, file_name, line_num
                    )
                    results["stats"] = summary
                elif line.startswith(finished_sentinel):
                    results["finished"] = True
                elif line.startswith(paused_sentinel):
                    logger.warning(
                        "%s on %s: Robocopy not finished (paused then killed)",
                        park,
                        date,
                    )
                    results["finished"] = False
            except Exception as ex:
                logger.error(
                    (
                        "Unexpected exception processing log, "
                        "file: %s, line#: %d, line: %s, exception: %s"
                    ),
                    file_name,
                    line_num,
                    line,
                    ex,
                )
        if saved_error:
            # could happen if there was a error retrying that was not resolved
            # before the file ended
            results["errors"].append(saved_error)  # logs a non-failing error
    return results


def clean_db(db_name):
    """Clean and recreate the log file database."""

    with sqlite3.connect(db_name) as conn:
        db_clear(conn, drop=False)
        db_create(conn)


def db_clear(database, drop=True):
    """Delete all records in all Tables and drop all indexes in the log file database."""

    try:
        cursor = database.cursor()
        if drop:
            cursor.execute("DROP INDEX IF EXISTS changes_date_ix")
            cursor.execute("DROP INDEX IF EXISTS logs_date_ix")
            cursor.execute("DROP TABLE IF EXISTS logs")
            cursor.execute("DROP TABLE IF EXISTS stats")
            cursor.execute("DROP TABLE IF EXISTS errors")
            cursor.execute("DROP TABLE IF EXISTS changes")
        else:
            cursor.execute("DELETE FROM logs")
            cursor.execute("DELETE FROM stats")
            cursor.execute("DELETE FROM errors")
            cursor.execute("DELETE FROM changes")
        database.commit()
    except sqlite3.OperationalError:
        pass


def db_create(database):
    """Build any missing tables and indexes in the log file database."""

    cursor = database.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs(
            log_id INTEGER PRIMARY KEY,
            park TEXT,
            date TEXT,
            filename TEXT,
            finished INTEGER);
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS logs_date_ix ON logs(date);
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stats(
            stat_id INTEGER PRIMARY KEY,
            log_id INTEGER NOT NULL,
            stat TEXT,
            copied INTEGER,
            extra INTEGER,
            failed INTEGER,
            mismatch INTEGER,
            skipped INTEGER,
            total INTEGER,
            FOREIGN KEY(log_id) REFERENCES logs(log_id));
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS error_codes(
            error_code INTEGER NOT NULL,
            error_name TEXT,
            UNIQUE(error_code));
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS errors(
            error_id INTEGER PRIMARY KEY,
            error_code INTEGER NOT NULL,
            log_id INTEGER NOT NULL,
            line_num INTEGER,
            failed INTEGER,
            message TEXT,
            FOREIGN KEY(error_code) REFERENCES error_codes(error_code),
            FOREIGN KEY(log_id) REFERENCES logs(log_id));
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS changes(
            date TEXT,
            UNIQUE(date));
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS changes_date_ix ON changes(date);
    """
    )
    database.commit()


def db_write_log(database, log):
    """Write a log file summary to the log file database."""

    cursor = database.cursor()
    cursor.execute(
        """
        INSERT INTO logs (park, date, filename, finished)
        VALUES (:park, :date, :filename, :finished)
    """,
        log,
    )
    log_id = cursor.lastrowid
    database.commit()
    return log_id


def db_write_stats(database, stats):
    """Write log file statistics to the log file database."""

    cursor = database.cursor()
    cursor.executemany(
        """
        INSERT INTO stats (log_id, stat, copied, extra, failed, mismatch, skipped, total)
        VALUES (:log, :stat, :copied, :extra, :failed, :mismatch, :skipped, :total)
    """,
        stats,
    )
    database.commit()


def db_write_errors(database, errors):
    """Write log file errors to the log file database."""

    cursor = database.cursor()
    cursor.executemany(
        """
        INSERT OR IGNORE INTO error_codes(error_code, error_name)
        VALUES(:code, :name)
    """,
        errors,
    )
    cursor.executemany(
        """
        INSERT INTO errors (error_code, log_id, line_num, failed, message)
        VALUES (:code, :log, :line_num, :failed, :message)
    """,
        errors,
    )
    database.commit()


def db_write_change(database, dates):
    """Write the data of PDS changes to the log file database."""

    cursor = database.cursor()
    cursor.executemany(
        """
        INSERT INTO changes (date)
        VALUES (:date);
    """,
        dates,
    )
    database.commit()


def main(db_name, log_folder):
    """Find all new log files and summarize in log file database."""

    filelist = glob.glob(os.path.join(log_folder, "*-update-x-drive.log"))
    if not filelist:
        logger.error("No robocopy log files were found")
    with sqlite3.connect(db_name) as conn:
        for filename in filelist:
            try:
                no_errors = True
                no_fails = True
                no_mismatch = True
                logger.info("Processing %s", filename)
                log = process_park(filename)
                if not log:
                    logger.error("The log object for %s is empty", filename)
                    continue
                for item in ["park", "date", "filename", "finished"]:
                    if item not in log:
                        logger.error(
                            'The log object for %s is bad; "%s" is missing',
                            filename,
                            item,
                        )
                        continue
                if log["finished"] is None:
                    logger.warning(
                        (
                            "%s on %s: Robocopy had to be killed "
                            "(it was copying a very large file when asked to pause)"
                        ),
                        log["park"],
                        log["date"],
                    )
                try:
                    log_id = db_write_log(conn, log)
                except sqlite3.Error as ex:
                    logger.error("Writing log %s to DB; %s", filename, ex)
                if not log_id:
                    logger.error("No Log ID returned from DB for log file %s", filename)
                    continue
                if "errors" in log:
                    for error in log["errors"]:
                        error["log"] = log_id
                        for attrib in ["code", "failed", "name", "line_num", "message"]:
                            if attrib not in error:
                                logger.error(
                                    "Bad errors object in log file %s, missing: %s in %s",
                                    filename,
                                    attrib,
                                    error,
                                )
                                continue
                        no_errors = False
                    try:
                        db_write_errors(conn, log["errors"])
                    except sqlite3.Error as ex:
                        logger.error(
                            "Writing errors for log %s to DB; %s", filename, ex
                        )
                if "stats" in log:
                    stats = []
                    for stat in ["dirs", "files", "bytes", "times"]:
                        if stat not in log["stats"]:
                            logger.error(
                                "Bad stats object in log file %s, missing: %s",
                                filename,
                                stat,
                            )
                            continue
                        obj = log["stats"][stat]
                        for item in [
                            "copied",
                            "extra",
                            "failed",
                            "mismatch",
                            "skipped",
                            "total",
                        ]:
                            if item not in obj:
                                logger.error(
                                    "Bad stats object in log file %s, missing: %s/%s",
                                    filename,
                                    stat,
                                    item,
                                )
                                continue
                        obj["log"] = log_id
                        obj["stat"] = stat
                        stats.append(obj)
                        if obj["failed"]:
                            no_fails = False
                        if obj["mismatch"]:
                            no_mismatch = False
                    try:
                        db_write_stats(conn, stats)
                    except sqlite3.Error as ex:
                        logger.error("Writing stats for log %s to DB; %s", filename, ex)
                else:
                    # We do not expect to get stats when robocopy didn't finish
                    # (finished == False or None)
                    if log["finished"]:
                        logger.error("No stats for log %s", filename)

                # In daily processing, I want an error email when there are
                #  issues in a log file currently even recovered errors send an error
                if not no_errors or not no_fails or not no_mismatch:
                    logger.warning("The log file %s has errors", filename)

            except Exception as ex:
                logger.error(
                    "Unexpected exception processing log file: %s, exception: %s",
                    filename,
                    ex,
                )
    clean_folder(log_folder)
    get_changes(db_name)


def clean_folder(folder):
    """Move processed log files to an archive folder."""

    year = datetime.date.today().year
    archive = "{0}archive".format(year)
    archive_path = os.path.join(folder, archive)
    if not os.path.exists(archive_path):
        os.mkdir(archive_path)
    filelist = glob.glob(os.path.join(folder, "*-update-x-drive.log"))
    filelist += glob.glob(os.path.join(folder, "*-update-x-drive-output.log"))
    filelist += glob.glob(os.path.join(folder, "*-robo-morning-kill.log"))
    for filename in filelist:
        try:
            new_name = os.path.join(archive_path, os.path.basename(filename))
            os.rename(filename, new_name)
        except Exception as ex:
            logger.error(
                "Unexpected exception moving log file: %s to archive %s, exception: %s",
                filename,
                new_name,
                ex,
            )
    # These log files do not have a date stamp, so be sure to remove the previous copy
    filelist = glob.glob(os.path.join(folder, "*-cmd.log"))
    for filename in filelist:
        try:
            new_name = os.path.join(archive_path, os.path.basename(filename))
            if os.path.exists(new_name):
                os.remove(new_name)
            os.rename(filename, new_name)
        except Exception as ex:
            logger.error(
                "Unexpected exception moving log file: %s to archive %s, exception: %s",
                filename,
                new_name,
                ex,
            )


def get_dates_from(change_log, since):
    """Open `change_log` and return a list of all dates greater than `since`.

    `change_log` is a file path to a change log file as described below.
    `since` must be a date string or None.

    `since` and dates in the `change_log` are 10 character strings in the format
    YYYY-MM-DD.

    It is assumed that:
    1) Change log dates are on a line all by themselves, followed by a line with
       exactly 10 dashes ("----------")
    2) Changes always go at the top of the file (newest on top), therefore we
       can stop scanning as soon as we see a date before `since`.
    3) Change log dates are in the past (a future date is logged as an error and
       ignored).

    Log an error and return none if an invalid or future date is found,
    otherwise return a list of all dates greater than `since`.
    """

    def real_date(text):
        try:
            datetime.date(int(text[:4]), int(text[5:7]), int(text[8:10]))
        except ValueError:
            return False
        return True

    dates = []
    today = datetime.date.today().isoformat()
    with open(change_log, "r", encoding="utf-8") as file_handle:
        previous_line = file_handle.readline()
        for line in file_handle:
            if line.strip() == "----------":
                date = previous_line[:10]
                if not real_date(date):
                    logger.error("Date (%s) is not a valid date.", date)
                    return None
                if date > today:
                    msg = "Change dates in the future (%s) are not allowed."
                    logger.error(msg, date)
                    return None
                if since is None or date > since:
                    # add a single element tuple to the list (for the db parameter substitution)
                    dates.append((date,))
                if since is not None and date <= since:
                    break
            previous_line = line
    return dates


def get_changes(db_name):
    """Find new dates in the change log and write them to the database.

    Dates in the database, and dates in the changelog are 10 character strings
    in the format YYYY-MM-DD. This will add all dates in the change log that
    occur before the first date found that is before the newest date in the
    database.
    """

    change_log = Config.change_log_path
    if not os.path.exists(change_log):
        logger.error("Change Log (%s) not found", change_log)
        return
    # if Change Log is older than last date in database, then skip
    # if no dates in datebase, then read all
    # otherwise, read changelog until date <= max_db_date
    max_db_date = None
    with sqlite3.connect(db_name) as conn:
        max_db_date = (
            conn.cursor().execute("SELECT MAX(date) FROM changes;").fetchone()[0]
        )
    unix_timestamp = os.path.getmtime(change_log)
    file_date = datetime.datetime.fromtimestamp(unix_timestamp).isoformat()[:10]
    if max_db_date is not None and file_date <= max_db_date:
        logger.info(
            "Changelog file date %s is not newer than the most recent change in the datebase %s",
            file_date,
            max_db_date,
        )
        return
    if max_db_date is None:
        logger.info("No change dates in the datebase, reading entire change log.")
    dates = get_dates_from(change_log, max_db_date)
    if dates is None:
        # error in change log was logged
        return
    if not dates:
        # no errors, but also no dates newer than database
        msg = "Change log was modified, but no new changes found. Check the change log."
        logger.error(msg)
        return
    dates.sort()
    with sqlite3.connect(db_name) as conn:
        try:
            db_write_change(conn, dates)
        except sqlite3.DatabaseError as ex:
            logger.error(
                "Unable to write new dates from changelog into database, error: %s", ex
            )


if __name__ == "__main__":
    try:
        # Warning: clean_db() will erase all records in the database.
        # clean_db(Config.database_path)
        main(Config.database_path, Config.log_folder)
    except Exception as ex:
        logger.error("Unexpected exception: %s", ex)
