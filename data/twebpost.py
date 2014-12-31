#!/home/rickldftp/anaconda/bin/python
# !/home/rick/anaconda3/envs/py278/bin/python
# !/C:Users\Rick\Anaconda\bin\python__author__ = 'rick'

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
    return dbfile  # we will return a file so we can test without data


def get_timestamp():
    if form.getvalue(u'timestamp'):
        timestamp = form.getvalue(u'timestamp')
        return timestamp
    return None


def get_newest_row():
    cmd = u"select timestamp, device, temperature from temperatures order by timestamp desc limit 1"
    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()
        rows = curs.execute(cmd)
        if rows != None:
            for row in rows:
                timestamp = row[0]
                deviceid = row[1]
                temperature = row[2]
                return timestamp, deviceid, temperature

#return the tdevice passed to the script
def get_tdevice():
    if form.getvalue(u'deviceid'):
        deviceid = form.getvalue(u'deviceid')
        return deviceid
    return None


def get_temperature():
    temperature = None
    if form.getvalue(u'temperature'):
        temperature = form.getvalue(u'temperature')
        return temperature
    return None


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

    succeeded = False
    dbfile = get_dbfile()
    timestamp = get_timestamp()
    if timestamp != None:
        deviceid = get_tdevice()
        if deviceid != None:
            temperature = get_temperature()
            if temperature != None:
                dbwrite(dbfile, timestamp, deviceid, temperature)
                succeeded = True
    # get the newest row to verify what was written, and so the poster can know what to post next
    timestamp, deviceid, temperature = get_newest_row()

    # print the HTTP header
    print u"Content-type: text/html\n\n"
    # print the page body
    print u"<body>"
    print u"<h1>tlogupdate data</h1>"
    info = u'dbfile="{0}", timestamp="{1}", deviceid="{2}", temperature="{3}"'.format(dbfile, timestamp, deviceid,
                                                                                      temperature)
    print info
    print u"</body>"
    print u"</html>"
    sys.stdout.flush()


if __name__ == u"__main__":
    main()

