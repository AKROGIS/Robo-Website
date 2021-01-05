# Robocopy Log Processor

This process is intended to be run as scheduled task to
summarize the several nightly robocopy log files into a database.

## `BufferingSMTPHandler.py`

A python 2.7 file to provide the logging service with the
ability to bundle multiple log messages into a single email.
`import`ed by `config_logger.py`

## `config_logger.py`

A python 2.7 file with a log configuration object that defines the how log
messages are formatted and where the messages at various log levels are written.
The logs can be written to the console (not useful for a scheduled task),
as well as a log file, email server, or database.  This file can be edited
to change how the different log messages are logged.  It must be
edited if the path or name of the database or log file is changed.

## `process_robo_logs_tests.py`

A python 2.7 file that was useful during development to test
the structure of the log files and to ensure that all the
possible errors and formats of the log files could be captured
correctly. It contains a lot of notes about the format and structure
of the robocopy log files. This file is no longer needed, but might be
helpful if a new version of robocopy changes the format of the log file.

## `process_robo_logs.py`

A python 2.7 file that reads unprocessed logs in the
[log folder](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L16)
and the 
[PDS change log](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L17)
and writes results to the
[log database](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L485).
It moves processed log files into a yearly archive sub folder.

This script should be run as a scheduled task. It should be run in the morning
after all the robocopy processes are completed.
(See the robocopy scripts in the
[PDS Data Management](https://github.com/AKROGIS/PDS-Data-Management/tree/master/robo-copy)
repo for details).
It should be run by an
account that has write permissions to the log folder and all files/folders
therein.  It also needs read permission to the PDS change log.

It is possible to use this script to clean the database (i.e. create a new
empty database), and reprocess all log files.  This shouldn't be required,
so details are not provided.  If needed, see the script for details.

## `SQLiteHandler.py`

A python 2.7 file to provide the logging service with the
ability to write logs to a sqlite3 database.
`import`ed by `config_logger.py`

## `X Drive - Robocopy Log Processor.xml`

A windows Schedule task export file.  This can be used to create the
scheduled task on a new server.  Be sure to verify the paths to the
python interpreter and the script working directory at the bottom of
this file.  The password for the service account that should run this task
is in the GIS Team password keeper, however the account is not a
login account and it is managed by IT.  Contact IT if the password expires.
**NOTE: When the pasword expires, the task will stop running.**