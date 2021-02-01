# This is a logger configuration dictionary.
# It is defined in https://docs.python.org/2/library/logging.config.html

config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'brief': {
            'format':  '%(name)-12s: %(levelname)-8s %(message)s',
        },
        'detailed': {
            'format':  '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            'datefmt': '%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        # command line arguments (--verbose and --debug will change the level of first handler to INFO and DEBUG)
        'console': {
            'class':     'logging.StreamHandler',
            'level':     'WARNING',
            'formatter': 'brief',
            'stream':    'ext://sys.stdout'
        },
        'file': {
            'class':     'logging.FileHandler',
            'level':     'INFO',
            'formatter': 'detailed',
            'filename':  'E:/Xdrive/Logs/LogProcessor.log'
        },
        'email': {
            # 'class':    'logging.handlers.SMTPHandler',  # Separate email for each message
            "class": "buffering_smtp_handler.BufferingSMTPHandler",
            'level':     'ERROR',
            'formatter': 'detailed',
            'mailhost': 'mailer.itc.nps.gov',
            'fromaddr': 'akro_gis_helpdesk@nps.gov',
            'toaddrs':  ['akro_gis_helpdesk@nps.gov'],
            'subject':  'Error running Robocopy Log Processor'
        },
        'sqlite': {
            'class': 'SQLiteHandler.SQLiteHandler',
            'level': 'ERROR',
            'db':    'E:/Xdrive/Logs/logs.db'
        }
    },
    'root': {
        'level': 'NOTSET',
        # 'handlers': ['console', 'file', 'sqlite']  # Do not send emails when testing
        'handlers': ['console', 'file', 'sqlite', 'email']  # Send emails in production
    }
}
