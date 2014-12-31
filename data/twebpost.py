__author__ = 'rick'

import cgi

form = cgi.FieldStorage()
import sqlite3
import sys
import cgitb
import os.path
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)
import ntpath
import matplotlib.dates
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange, date2num, num2date
import glob
import ntpath
import datetime

# print the HTTP header
def printHTTPheader():
    print u"Content-type: text/html\n\n"


# gets the database path and list of database names in it.
def get_dbnames():
    logger.debug("getting dblist")
    dbfiles = sorted(glob.glob(u'../tlogx/data/*.db'))
    if dbfiles == None or len(dbfiles) == 0:
        dbfiles = sorted(glob.glob(u'*.db'))
    # search for a devices file that start with 28
    if dbfiles == []:
        logger.critical(u'no databases found')
        return
    path = ntpath.split(dbfiles[0])[0]
    dbnames = []
    for dbfile in dbfiles:
        dbnames.append(ntpath.split(dbfile)[1])
    return path, dbnames


def get_dbfile():
    dbfile = None
    path, dbnames = get_dbnames()
    if form.getvalue(u'dbname'):
        dbname = form.getvalue(u'dbname')
        if dbname in dbnames:
            dbfile = os.path.join(path, dbname)
            return dbfile
    dbfile = os.path.join(path, 'tlog.db')
    return dbfile


def get_timestamp():
    if form.getvalue(u'timestamp'):
        timestamp = form.getvalue(u'timestamp')
        return timestamp
    return str(datetime.datetime.now())


#return the tdevice passed to the script
def get_tdevice():
    deviceid = None
    if form.getvalue(u'deviceid'):
        deviceid = form.getvalue(u'deviceid')
        return deviceid
    return 'dummydevice'


def get_temperature():
    temperature = None
    if form.getvalue(u'temperature'):
        temperature = form.getvalue(u'temperature')
        return temperature
    return float(85)


def dbwrite(dbfile, timestamp, deviceid, temperature):
    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()
        curs.execute("insert into temperatures (timestamp, device, temperature) values (?,?,?)",
                     [timestamp, deviceid, temperature])


# main function
# This is where the program starts
def main():
    global dbfile

    #enable debugging
    cgitb.enable()

    dbfile = get_dbfile()
    timestamp = get_timestamp()
    deviceid = get_tdevice()
    temperature = get_temperature()
    dbwrite(dbfile, timestamp, deviceid, temperature)

    # print the HTTP header
    printHTTPheader()
    print 'success'
    sys.stdout.flush()


if __name__ == u"__main__":
    main()

