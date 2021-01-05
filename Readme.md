# Robocopy Status Monitor

This repo contains three components required to monitor the status of the
nightly robocopy of the GIS data server to remote data servers at the Parks.
The three components are:

* **Processor** -- runs nightly to distill the robocopy log files (text)
  into a database (sqlite3).
* **Server** -- a python http(s) server that listens for report requests and
  reads the log database to return json objects representing the
  requested report.
* **Website** -- Presents the status of the robocopy process by requesting
  reports from the server and formatting the reports in a web page.

## Build

There is no build step required for any of the components to be deployed.

## Deploy

### Processor

* Verify that the paths and file names in `processor/process_robo_logs.py`
and `processor/config_logger.py` are correct. See the
[processor/Readme.md](https://github.com/AKROGIS/Robo-Website/tree/master/processor/Readme.md)
for details.

* Copy all the python files (except `*_test.py`) in the processor folder to
a folder adjacent to the location where the robocopy log files are written
(by the robocopy scripts in the
[PDS Data Management](https://github.com/AKROGIS/PDS-Data-Management/tree/master/robo-copy)
repo).

* Verify that python 2.7 is installed on the server.  No special modules
are required.

* Create and deploy a scheduled task to run `process_robo_logs.py`.  See
the processor readme for details.

### Server

* Verify that the
[database path](https://github.com/AKROGIS/Robo-Website/blob/master/server/Server.py#L10)
in `server/Server.py` matches the path set above for the
processor.

* Copy `server/Server.py` to the server where the processor is deployed.

* Copy the TLS certificate files to the folder where `server.py` is
deployed.  See `Projects\AKR\ArcGIS Server` in the GIS Team network drive for
details on obtaining and deploying the certificates. The certificate file
names must match
[server.py](https://github.com/AKROGIS/Robo-Website/blob/master/server/Server.py#L430).

* Create and deploy a scheduled task to start this task when the server
restarts, and if the task ever dies (it should run forever).  The task
needs to be run with an account that can read the processor log database.

### website

* Verify the
[service path](https://github.com/AKROGIS/Robo-Website/blob/master/website/script.js#L6)
in `website\script.js` matches the server and port set above at the end of
`server.py`

* Copy the files in the `website` folder to to any published folder
on a web server.  Check the website to make sure it can query the
server deployed above.

* The website also serves the `PDS_ChangeLog.html`.  There is a scheduled task
that needs to run that can copy this file from its home on the GIS data server,
to this website folder.  For security reasons, the website does not have
access to the data server.

## Using

Point your browser to the directory where the website is published.  GIS
users should be encouraged to check the website if they are concerned
that the data at their park is not up to date.

### PDS Data Manager

The data manager should check the website daily for issues.

#### Robocopy Issues

Most robobopy issues are temporary (remote server down, or intermittent
network issues).  Issues that persist can usually be resolved by contacting
park IT staff.

#### Processing Issues

Occasionally there are issues with the processing and or serving of the
robocopy logs.  If the website is unable to get the reports, check
that the scheduled tasks for the server and processor are running.

The data manager should check the log file (configured in
[processor/config_file.py](https://github.com/AKROGIS/Robo-Website/blob/master/processor/config_logger.py#L28))
for issues, and be on the alert for emails (configured in
[processor/config_file.py](https://github.com/AKROGIS/Robo-Website/blob/master/processor/config_logger.py#L37))
from the log processor. This will happen if there is some error
in processing a log file (very rarely happens).

It may happen that there is a log processing error that writes
incorrect data into the log database. If that happens copy the
[database](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L485)
to a local directory and use the
[sqlite3 command line tool](https://sqlite.org/cli.html)
to issue SQL commands to query and correct the database.  See
[processor/processor/process_robo_logs.py](https://github.com/AKROGIS/Robo-Website/blob/master/processor/process_robo_logs.py#L239-L290)
for the database schema.  After the database is repaired, copy it back to
its home in the log folder on the server.
