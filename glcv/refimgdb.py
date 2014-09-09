#!/bin/env python
# /****************************************************************************
# * Name:       refimgdb.py
# * Author:     Chris Holden (ceholden@bu.edu) & Max Metcalfe (maxm@bu.edu)
# * Version:    1.0
# * Purpose:    To interface with GLC Validation database providing command
# *             line and.onsole methods for viewing and updating tables.
# * Methods:    Command line interface parser available. If no arguments
# *             specified, defaults to console. Uses Python's sqlite3 library
# *             to update or view tables.
# *
# * Copyright (c) 2012, Chris Holden
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.
# *****************************************************************************\
import argparse
import codecs
import cStringIO
import csv
import os
import readline
import sys
import sqlite3

###
# Global variable set for debugging purposes
###
setdebug = False

###
# Class for auto-completion
###
class DBCompleter:
    def __init__(self, volcab):
        self.volcab = volcab
        self.text = None
        readline.parse_and_bind("tab: complete")

    def complete(self, text, state):
        results = [x for x in self.volcab if x.startswith(text)] + [None]
        return results[state]

###
# Help function
###
def console_help():
    print "Not implemented yet..."

###
# Utility functions
###

# Type checking for user input
# Returns true/false if input is an int
def checkInt(string):
    if string is not None:
        try:
            int(string)
            return True
        except ValueError:
            return False
    else:
        return False

def getColumnNames(db):
    # Get cursor
    cursor = db.cursor()
    # Get all
    cursor.execute('SELECT * FROM site')

    desc = list(col[0] for col in cursor.description)
    return desc

def getDates(db, fid):
    # Get cursor
    cursor = db.cursor()
    # Get all dates for fid
    command = 'SELECT %s FROM site WHERE fid=:id' % 'image_date'
    cursor.execute(command, {'id':fid})
    
    # Convert from Unicode and into list
    dates = [str(d[0]) for d in cursor.fetchall()]
    
    return dates

###
# Function that opens database
###
def openDB():
    path = "/projectnb/modislc/projects/glcv/docs/database/glcv_db.sqlite"
    
    # Open db connection with parsing of types
    # See: http://stackoverflow.com/questions/4272908
    db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    print 'Opened database: ' + path
    #db.text_factory = lambda x: unicode(x, "utf-8", "ignore")

    return db

###
# Main functions for user interaction. Includes raw_input prompts and checks on
# user input. Used only for terminal mode
###
# Prompt user for FID
def promptFID():
    success = False
    while success == False:
        # Get FID
        fid = raw_input("FID?: ")
        # Check
        if not checkInt(fid):
            print 'Error: FID must be an integer'
        else:
            fid = int(fid)
            success = True

    return fid

# Prompt user for date of imagery
# Returns date as String or None
def promptDate(db, fid, required):
    # Set success flag to required so asks for get, not for update
    success = required
    # Set selectDate to required, get users can make this False
    selectDate = required

    # Get possible dates for FID
    dates = getDates(db, fid)
    # Only prompt for dates if more than one date
    if len(dates) > 1:
        while success == False:
            selectDate = raw_input("Select a date?: Y/N\n").lower()
            if selectDate == 'yes' or selectDate == 'y':
                selectDate = True
                success = True
            elif selectDate == 'no' or selectDate == 'n':
                selectDate = False
                success = True
            else:
                print 'Error: specify yes/no'
    else:
        print 'Date: ' 
        print dates
        date = dates[0]
        selectDate = False
    # Prompt user to select date if wanted/required
    if selectDate:
        print 'Dates: '
        print dates
        # Setup autocomplete
        completer = DBCompleter(dates)
        readline.set_completer(completer.complete)
        # Start prompt
        success = False
        while success == False:
            date = raw_input('Select date: ')
            if date not in dates:
                print 'Error: invalid date selected.'
            else:
                success = True
    # If not wanted/required, set to None
    else:
        date = None

    # Undo completer
    readline.set_completer(None)
    
    # Return
    return date

# Prompt user for column to select column in database
# Returns column name as String or None
def promptColumn(db, required):
    # Set chosen to value of required
    # get - not required, chosen is False - prompts for input
    # update - required, chosen is True - doesn't prompt
    chosen = required
    # Set chooseColumn to required, user can change to True if get
    chooseColumn = required
    while chosen == False:
        chooseColumn = raw_input("Select a column?: Y/N\n").lower()
        if chooseColumn == "yes" or chooseColumn == "y":
            chooseColumn = True
            chosen = True
        elif chooseColumn == "no" or chooseColumn == "n":
            if required:
                print 'Error: column selection required for updating'
            else:
                chooseColumn = False
                chosen = True
        else:
            print 'Error: specify yes/no'

    # If user wants to pick column
    if chooseColumn:
        # Show user column names
        columns = getColumnNames(db)
        print 'Possible column names: '
        print columns

        # Setup completer
        completer = DBCompleter(columns)
        readline.set_completer(completer.complete)
        # Start prompt
        chosen = False
        while chosen == False:    
            column = raw_input("Select a column: ").lower()
            # Check if column is available
            if column not in columns:
                print 'Error: no such column name'
            else:
                chosen = True
            
    else:
        column = None

    # Reset completer
    readline.set_completer(None)
    # Return column name or None if not selected
    return column

# Prompt user for value to update column with
def promptValue():
    success = False
    while success == False:
        value = raw_input('Input new value: ')
        if value is not None:
            success = True
    return value

# Checks value input by user against dictionary of acceptable values
def checkValue(column, value):
    # Create a dictionary of lists
    # Key - column name
    # Value - acceptable values
    d = dict([('class_progress', list(['Unassigned',
                                       'Assigned',
                                       'Complete - unedited',
                                       'Complete - edited',
                                       'Complete - another date'])),
              ('interp_progress', list(['incomplete', 'in progress', 'review',
                                        'complete']))])
    # Check if column is in dictionary
    if column in d.keys():
        # Check if value is in acceptable list
        if value.lower() in [x.lower() for x in d[column]]:
            # Get index of value in acceptable list
            index = [x.lower() for x in d[column]].index(value.lower())
            value = d[column][index]
        else:
            print 'Error: unacceptable entry. Use the following: '
            print d[column]
            value = None

    return value 

###
# Main input prompt script. Calls other functions for input, parsing, and
# applying.
###
def inputPrompt(db):
    # Possible options
    options = ["get", "update", "help", "exit", "debug", "console", "output"]
    # Setup completer
    completer = DBCompleter(options)
    readline.set_completer(completer.complete)
    
    # Print options
    print 'Possible actions: GET, UPDATE, OUTPUT, HELP, EXIT'
    choice = raw_input("Action?: ")
    # Check user input
    if (choice.lower() in options) is False:
        print 'Error: unknown action'
        # Do not exit
        return False

    print 'Action chosen: ' + choice.lower()

    # Clear readline history (i.e. so a 'get' doesn't show up once in get input
    # function
    readline.clear_history()

    # Handle logic for each option
    if choice.lower() == 'get':
        # Get FID
        fid = promptFID()
        # Get date, not required
        date = promptDate(db, fid, False)
        # Get column, does not require a column return
        column = promptColumn(db, False)
        # We've parced user input, show info
        print '<----------Result for FID %s---------->' % fid 
        cursor = queryFID(db, fid, date, column)
        print '<-----SEARCH RESULT----->'  
        print_query(cursor)
        # Return false to continue after action
        return False
    elif choice.lower() == 'update':
        # Get FID
        fid = promptFID()
        # Get date, requires a non-None return
        date = promptDate(db, fid, True)
        # Get column, requires a non-None return
        column = promptColumn(db, True)
        # Show user current value
        current_cursor = queryFID(db, fid, date, column)
        print '<-----CURRENT VALUE----->'
        print_query(current_cursor)
        # Ask for user to input value; check if input sane
        success = False
        while success == False:
            # Prompt for value for column
            value = promptValue()
            # Check if value is successful
            value = checkValue(column, value)
            if value is not None:
                success = True
                print 'Using value: ' + value
        # We've parced user input, update
        updateFID(db, fid, date, column, value)
        # Return false to continue after action...
        return False
    elif choice.lower() == 'output':
        outputTable(db)
        return False
    elif choice.lower() == 'help':
        console_help()
        return False
    elif choice.lower() == 'exit':
        print 'Goodbye!'
        db.close()
        return True
    elif choice.lower() == 'debug':
        # Accessing global variable for debugging
        global setdebug
        # Switching value
        if setdebug:
            setdebug = False
            print 'Debugging off'
        else:
            setdebug = True
            print 'Debugging: on'
        # Return false to continue after action...
        return False
    elif choice.lower() == 'console':
        print 'Entering console mode... type "exit" to return.'
        start_console(db)
        return False
        
###
# Functions to get/update database. Used by both terminal and command line.
###
# Function to query DB for FID/date
def queryFID(db, fid, date, column):
    # Get cursor
    cursor = db.cursor()

    # Check if column is specified
    if date is None and column is None:
        command = '''
        SELECT * 
        FROM site 
        WHERE fid=:id;
        '''
    elif date is None and column is not None:
        command = '''
        SELECT %s
        FROM site
        WHERE fid=:id;
        ''' % column
    elif date is not None and column is None:
        command = '''
        SELECT *
        FROM site
        WHERE fid=:id AND
        image_date=:date;
        '''
    elif date is not None and column is not None:
        command = '''
        SELECT %s
        FROM site
        WHERE fid=:id AND
        image_date=:date;
        ''' % column

    if date is None:
        cursor.execute(command, {"id":fid})
    else:
        cursor.execute(command, {"id":fid, "date":date})

    return cursor

# Function to print cursor result from execute query
def print_query(cursor):
    # Get a result from cursor
    result = cursor.fetchone()
    while result is not None:
        count = 0
        print ' ' # print for new line
        for col in cursor.description:
            if result is not None:
                if checkInt(result[count]):
                    print col[0] + ": " + str(result[count])
                else:
                    print col[0] + ": " + result[count].encode('utf-8')
            else:
                print row[0] + ": None"
            count += 1
        result = cursor.fetchone()
    print ' ' # print for new line

# Function to query DB and update FID/date
def updateFID(db, fid, date, column, value):
    # Get cursor
    cursor = db.cursor()

    # Check if column is specified - needs to be for updates
    if column is None:
        print 'Error: updating database requires a column'
    elif value is None:
        print 'Error: cannot update database with null value'
    elif fid is None:
        print 'Error: must select a FID'

    command = '''
    UPDATE site
    SET %s=:value
    WHERE fid=:id;
    ''' % column

    # Execute commmand
    cursor.execute(command, {"value":value, "id":fid})
    # Check data type from update command
    try:
        cursor.execute("SELECT * FROM site WHERE fid=(?)", (fid,))
    except ValueError as err:
        print 'Error: invalid data type for selected column'
        print(err)
        conn.rollback()
    # Commit
    db.commit()

def outputTable(db):
    print 'Output valid SQL query to CSV'
    # Get cursor
    cursor = db.cursor()
    # Set boolean for successful user input
    success = False
    # Prompt for output filename
    while not success:
        print 'Enter filename'
        filename = raw_input('> ')
        # Check that user input something...
        if len(filename) > 0:
            # Check if file extension
            ext = filename.split('.')[-1]
            if ext.lower() != 'csv':
                # Append csv
                filename = filename + '.csv'
            success = True
    # We have filename, query delimiter
    success = False
    while not success:
        print 'Enter delimiter'
        delim = raw_input('> ')
        # Check user input something
        if len(delim) > 0:
            success = True
    # We have filename and delim, prompt for query
    success = False
    while not success:
        print 'Enter a select query'
        query = raw_input('> ')
        # Check if select
        if query.split(' ')[0].lower() != 'select':
            print 'Error: query must be a select statement'
        # Check if contains "drop"...
        elif 'drop' in query.lower():
            print 'Warning: check against "drop" in query failed.'
        else:
            # Execute query
            try:
                cursor.execute(query)
            except sqlite3.OperationalError:
                print 'Error: invalid sqlite3 input'
                continue
            # Create writer for output
            writer = UnicodeWriter(open(filename, 'wb'), delimiter=delim)
            # Output header
            header = list(col[0] for col in cursor.description)
            writer.writerow(header)
            # Write query
            writer.writerows(cursor)
            success = True


def start_console(db):
    """
    Console mode - for advanced users. Allows direct input of sqlite3 commands
    """
    # Warnings...
    print 'Warning: for advanced users only. You must commit changes manually.'
    # Get cursor
    cursor = db.cursor()
    # Note: readline has been imported; raw_input has history & line editing 
    # Boolean to close prompt
    close = False
    while close == False:
        # Get user input
        input = raw_input('> ')
        # Check if not "exit" command
        if input.lower() == 'exit':
            close = True
        elif input.lower() == 'commit':
            # Committing database
            db.commit()
        else:
            try:
                cursor.execute(input)
            except sqlite3.OperationalError:
                print 'Error: invalid sqlite3 input' 
            # If input had select statement, print it
            if 'select ' in input.lower():
                print_query(cursor)

    # Do not exit program
    return False

def main():
    #TODO: write description
    desc = "TODO"
    parser = argparse.ArgumentParser(prog="refimgdb.py", description=desc)

    parser.add_argument('-action', action='store', dest='action', type=str,
                        help='Action to perform (get, update)')
    parser.add_argument('-fid', action='store', dest='fid', type=int,
                        help='FID of image')
    parser.add_argument('-date', action='store', dest='date', type=str,
                        help='Date of image')
    parser.add_argument('-column', action='store', dest='column', type=str,
                        help='Database column')
    parser.add_argument('-value', action='store', dest='value', type=str,
                        help='Update column with value')

    args = parser.parse_args()

    db = openDB()
    
    # Check if command lines arguements used
    if (args.action is None and args.fid is None and args.date is None 
        and args.column is None and args.value is None):
        # Create variable for user exiting
        exited = False
        while exited == False:
            exited = inputPrompt(db)
            readline.clear_history()
    # If command line argument, perform actions accordingly
    else:
        # Check if user specified a usable action
        possible_action = ['get', 'update']
        if (args.action in possible_action) is False:
            print 'Error: action not possible'
            print parser.print_help()
            sys.exit(1)
        else:
            if args.action == 'get':
                cursor = queryFID(db, args.fid, args.date, args.column)
                print_query(cursor)
            elif args.action == 'update':
                updateFID(db, args.fid, args.date, args.column, args.value)

    db.close()
    sys.exit(0)

# UnicodeWriter class
# Source: https://gist.github.com/2564099
class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    Source: http://docs.python.org/library/csv.html#csv-examples
    Modified to cope with non-string columns.
    """

    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def encodeone(self, item):
        if type(item) == unicode:
            return self.encoder.encode(item)
        else:
            return item

    def writerow(self, row):
        self.writer.writerow([self.encodeone(s) for s in row])
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

if __name__ == "__main__":
    main()
