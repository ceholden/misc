#!/usr/bin/env python
""" Update SQLite3 Database

Usage:
    update_sqlite3_db.py [options] <database> <csvfile>

Options:
    -t --table <table>          Table to select [default: site]
    -w --where <columns>        Columns to select [default: fid]
    -d --delimit <delimiter>    Delimiter for CSV file [default: ,]
    -q --quotechar <quotechar>  Quote character [default: "]
    -v --verbose                Show verbose debugging options
    --quiet                     Be quiet
    -h --help                   Show help messages
"""
from docopt import docopt

import csv
import os
import sqlite3
import sys

VERBOSE = False
QUIET = False

def update_sqlite3_db(database, csvfile, table, where, delimit, quotechar):
    """
    Open database file updating where specified in CSV file
    """
    print database
    print csvfile
    print table
    print where
    print delimit
    print quotechar

def main():
    """
    Parse arguments and hand to update_sqlite3_db
    """
    # SQLite3 database file
    database = arguments['<database>']
    if not os.path.exists(database):
        print 'Error: database file does not exist'
        sys.exit(1)
    elif not os.access(database, os.W_OK):
        print 'Error: database file is not writable'
        sys.exit(1)
    
    # Input CSV file
    csvfile = arguments['<csvfile>']
    if not os.path.exists(csvfile):
        print 'Error: CSV file does not exist'
        sys.exit(1)
    elif not os.access(csvfile, os.R_OK):
        print 'Error: CSV file is not readable'
        sys.exit(1)

    # Table
    table = arguments['--table']

    # Database columns to select where
    where = arguments['--where']
    where = where.replace(', ', ' ').split(' ')

    # CSV file delimiter
    delim = arguments['--delimit']

    # Quote character
    quotechar = arguments['--quotechar']

    update_sqlite3_db(database, csvfile, table, where, delim, quotechar)

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--verbose']:
        VERBOSE = True
    if arguments['--quiet']:
        QUIET = True
    main()
