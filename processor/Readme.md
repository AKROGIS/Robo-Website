# Robocopy Log Processor

This process is intended to be run a scheduled task to
summarize the several nightly robocopy log files into a database.

## `processor/BufferingSMTPHandler.py`

A python 2.7 file to provide the logging service with the
ability to bundle multiple log messages into a single email.
`import`ed by `config_file.py`

## `processor/config_logger.py`

A python 2.7 file with the log configuration object which defines the how
log messages are formatted, and where the various log levels are written.
The logs can be written to the console (not useful for a scheduled task),
as well as a log file, email server, or database.  This file can be edited
to change how the different log messages are logged.  It must be
edited if the path or name of the database or log file is changed.

## `processor/process_robo_logs_tests.py`

A python 2.7 file that was useful during development to test
the structure of the log files and to ensure that all the
possible errors and formats of the log files could be captured
correctly. It captures a \lot of notes about the format and structure
of the robocopy log format. This file is no longer needed, but might be
helpful if a new version of robocopy changes the format of the log file.

## `processor/process_robo_logs.py`

A python 2.7 file that reads unprocessed logs in the
[log folder](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L16)
and the 
[PDS change log](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L17)
and writes results to the
[log database](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L485)
and moves processed log files into a yearly archive sub folder.

This script should be run as a scheduled task. It should be run in the morning
after all the robocopy processes are completed.  It should be run by an
account that has write permissions to the log folder and all files/folders
therein.  It also needs read permission to the PDS change log.

It is possible to use this script to clean the database (i.e. create a new
empty database), and reprocess all log files.  This shouldn't be required,
so details are not provided.  If needed, see the script for details.

## `processor/SQLiteHandler.py`

A python 2.7 file to provide the logging service with the
ability to write logs to a sqlite3 database.
`import`ed by `config_file.py`
