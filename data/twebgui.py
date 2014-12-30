#!/home/rickldftp/anaconda/bin/python
# !/home/rick/anaconda3/envs/py278/bin/python
#!/C:Users\Rick\Anaconda\bin\python


#this file gets copied to /var/www  (eventualy it should be the cgi-bin folder)


from __future__ import division
from __future__ import with_statement
import datetime
import matplotlib
import numpy
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange, tdnum, num2date

from pylab import savefig
from optparse import OptionParser
import sqlite3
import sys
import cgi
import cgitb
import os.path
import dateutil.parser as dparser

import io
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import glob
import ntpath
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


# global variables
speriod = (15 * 60) - 1
dbfile = None

form = cgi.FieldStorage()

#gets the database path and list of database names in it.
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


# print the HTTP header
def printHTTPheader():
    print u"Content-type: text/html\n\n"


# print the HTML head section
# arguments are the page title and the table for the chart
def printHTMLHead(title, table):
    print u"<head>"
    print u"    <title>"
    print title
    print u"    </title>"
    print u"</head>"


# get data from the database
# if an interval is passed,
# return a list of records from the database
def get_tdata(tdeviceId, starttime, endtime):
    global dbfile
    temperatures = []
    mintemp = 100
    maxtemp = -100
    mintempdate = sys.float_info.max
    maxtempdate = 0;

    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()

        cmd = u"SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>=datetime('{1}') AND timestamp<=datetime('{2}') order by timestamp limit 10000".format(
            tdeviceId, starttime, endtime)
        curs.execute(cmd)
        rows = curs.fetchall()
        dates = []
        for row in rows:
            dt = date2num(datetime.datetime.strptime(row[0], u"%Y-%m-%d %H:%M:%S.%f"))
            dates.append(dt)
            temp = float(row[1])
            temperatures.append(temp)
            if mintemp > temp:
                mintemp = temp
                mintempdate = dt
            if maxtemp < temp:
                maxtemp = temp
                maxtempdate = dt
        avgtemp = "NA"

    return dates, temperatures, mintempdate, mintemp, maxtempdate, maxtemp, avgtemp


# convert rows from database into a javascript table
def create_table(dates, temperatures, heaterdates, heateronpoints):
    def Tf(Tc):
        return (Tc * 9. / 5.) + 32

    def Tc(Tf):
        return (Tf - 32) * 5. / 9.

    def update_ax2(ax):
        y1, y2 = ax.get_ylim()
        ax2.set_ylim(Tf(y1), Tf(y2))
        ax2.figure.canvas.draw()

    # majorLocator   = MultipleLocator((maxdate-mindate)/20)
    # majorFormatter = FormatStrFormatter('%D')
    # minorLocator   = MultipleLocator((maxdate-mindate)/5)

    fig, ax = plt.subplots()  # ax is the Celsius scale
    fig.set_size_inches(14, 4)

    ax2 = ax.twinx()  # ax2 is the Fahrenheit scale
    ax2.yaxis.tick_left()
    ax.yaxis.tick_right()
    ax.callbacks.connect("ylim_changed", update_ax2)
    ax.plot_date(dates, temperatures, u'b-')
    if heateronpoints != None:
        ax.plot_date(heaterdates, heateronpoints, u'r-')
    ax.autoscale_view()
    # ax.xaxis.set_major_locator(majorLocator)
    # ax.xaxis.set_major_formatter(majorFormatter)

    #for the minor ticks, use no labels; default NullFormatter
    # ax.xaxis.set_minor_locator(minorLocator)

    ax.grid(True)

    fig.autofmt_xdate()
    savefig(u'../tchart.png', dpi=80, bbox_inches=u'tight')


# # Save the image to buffer
# buf = io.BytesIO()
# fig.savefig(buf, format='png')
#out = buf.getvalue()
#buf.close()
#print ('Content-Type: image/png\n')
#print (out)


def getheaterontime(dates, temperatures, device_type):
    if device_type != 'heater':
        return None, None, None
    heateronslope = 3000  # slope that says heater has started. deg/day
    heateroffslope = -400  # slope that says heater has stopped.
    heaterontime = float(0)
    heaterison = False
    heaterdates = []
    heatervalues = []
    tdiff = max(temperatures) - min(temperatures)
    tmin = min(temperatures)
    on = tmin + tdiff
    off = tmin

    for i in (range(0, len(dates) - 1)):
        tdelta = temperatures[i + 1] - temperatures[i]
        ddelta = dates[i + 1] - dates[i]
        slope = tdelta / ddelta
        if heaterison:
            if (slope < heateroffslope):
                heaterison = False
                heaterdates.append(dates[i] - 0.000001)  # ~ 1/10 second
                heatervalues.append(on)
                heaterdates.append(dates[i])
                heatervalues.append(off)
        else:
            if (slope > heateronslope):  # add more conditions so we get the time after heater is as hot as it gets.
                heaterison = True
                heaterdates.append(dates[i] - 0.000001)  # ~ 1/10 second
                heatervalues.append(off)
                heaterdates.append(dates[i])
                heatervalues.append(on)
        if heaterison:
            heaterontime = heaterontime + ddelta

    return heaterontime, heaterdates, heatervalues


def get_degree_days_diff(dates1, temperatures1, dates2, temperatures2):
    degdays1 = numpy.trapz(temperatures1, dates1)
    degdays2 = numpy.trapz(temperatures2, dates2)
    return degdays1 - degdays2


def get_degree_days(insideID, outsideID, starttime, endtime):
    # todo to take care of difference in start and endtimes by interpolation
    dates, temperatures, mintempdate, mintemp, maxtempdate, maxtemp, avgtemp = get_tdata(insideID, starttime, endtime)
    degdays1 = numpy.trapz(temperatures, dates)
    dates, temperatures, mintempdate, mintemp, maxtempdate, maxtemp, avgtemp = get_tdata(outsideID, starttime, endtime)
    degdays2 = numpy.trapz(temperatures, dates)
    return degdays1 - degdays2


def timedeltatostring(timedelta):
    totalleft = timedelta * 24
    hours = int(totalleft)
    totalleft = (totalleft - hours) * 60
    minutes = int(totalleft)
    totalleft = (totalleft - minutes) * 60
    seconds = int(totalleft)
    str = "{0:02.0f}:{1:02.0f}:{2:02.0f}".format(hours, minutes, seconds)
    return str


# print the div that contains the graph
def show_graph_title(starttime, endtime, tdevice):
    hours = (endtime - starttime).total_seconds() / 3600
    print u"<h2>{0} (deviceid={1})</h2>".format(tdevice[1], tdevice[0])
    print u"<h2>Temperature Chart from {0} to {1} ({2:.0f} hours)</h2>".format((str(starttime))[:-10],
                                                                               (str(endtime))[:-10], hours)


#    print u'<div id="chart_div" style="width: 1500px; height: 50px;"></div>'

def datstr(datnum):
    # hours = datestr(furnaceontime, 'DD HH:MM:SS')
    total_seconds = int(datnum * 24 * 60 * 60)
    days, remainder = divmod(total_seconds, 24 * 60 * 60)
    hours, remainder = divmod(total_seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    string = '{0:.0f} {0:02.0f}:{1:02.0f}:{2:02.0f}'.format(days, hours, minutes, seconds)
    return string


# connect to the db and show some stats
# argument option is the number of hours
def show_stats(dates, temperatures, mindate, mintemp, maxdate, maxtemp, avgtemp, starttime, endtime, furnaceontime,
               tdevice, heatingdegreedays):
    rowstrmax = u"{2:6.1f}F ({1:5.2f}C) at {0}".format(displaydatetime(maxdate), maxtemp, maxtemp * 9 / 5 + 32)
    rowstrmin = u"{2:6.1f}F ({1:5.2f}C) at {0}".format(displaydatetime(mindate), mintemp, mintemp * 9 / 5 + 32)

    print u'<h2>'
    if furnaceontime != None and heatingdegreedays != None:
        furnacepercent = int(furnaceontime / (dates[len(dates) - 1] - dates[0]) * 100)
        furnacehours = datstr(furnaceontime)
        print u'Heat time={0} ({1:.0f}% '.format(furnacehours, furnacepercent)
        print u'Heat degree days={0:.2f} HeatTime/KDegDay={1:.6f}</h2>'.format(heatingdegreedays * 9 / 5,
                                                                               1000 * furnaceontime / heatingdegreedays)
    print u'</h2>'
    print '<h2>Low {0}, High {1}</h2>'.format(rowstrmin, rowstrmax)

    print u"<h2>Temperature Points:</h2>"
    print u"<table>"
    print u"<tr><td><strong>Date/Time</strong></td><td><strong>Temp C</strong></td><td><strong>Temp F</strong></td></tr>"

    for i in range(0, len(dates)):
        tf = float(temperatures[i]) * 9 / 5 + 32
        tc = float(temperatures[i])
        rowstr = u"<tr><td>{0}&emsp;&emsp;</td><td>{1:7.2f} C</td><td>{2:7.1f} F</td></tr>".format(
            displaydatetime(str(num2date(dates[i]))[:-6]), tc, tf)
        print rowstr
    print u"</table>"
    print u"<hr>"


def print_options_selector(dbname, deviceid, hours, dbnames):
    print u"<form action=\"twebgui.py\" method=\"GET\">"
    print u" Show the temperature logs for "
    print u"<select name=\"hours\">"
    if hours is not None:
        ti = float(hours)
        if ti < 0:
            ti = 1
            hours = 1
        if ti == 1:
            print u"<option value=\"1.0\" selected=\"selected\">the last hour</option>"
        else:
            print u"<option value=\"1.0\">the last hour</option>"

        if ti == 6:
            print u"<option value=\"6.0\" selected=\"selected\">the last 6 hours</option>"
        else:
            print u"<option value=\"6.0\">the last 6 hours</option>"

        if ti == 12:
            print u"<option value=\"12.0\" selected=\"selected\">the last 12 hours</option>"
        else:
            print u"<option value=\"12.0\">the last 12 hours</option>"

        if ti == 24:
            print u"<option value=\"24.0\" selected=\"selected\">the last day</option>"
        else:
            print u"<option value=\"24.0\">the last 24 hours</option>"
        if ti == 48:
            print u"<option value=\"48.0\" selected=\"selected\">the last 2 days</option>"
        else:
            print u"<option value=\"48.0\">the last 2 days</option>"
        if ti == 168:
            print u"<option value=\"168.0\" selected=\"selected\">the last week</option>"
        else:
            print u"<option value=\"168.0\">the last week</option>"
        if not ti in [1, 6, 12, 24, 48, 168]:
            print '<option value="{0:.1f}" selected="selected">the last {0:.1f} hours</option>'.format(ti)



    else:
        print u"<option value=\"1.0\">the last hour</option>"
        print u"<option value=\"6.0\">the last 6 hours</option>"
        print u"<option value=\"12.0\">the last 12 hours</option>"
        print u"<option value=\"24.0\" selected=\"selected\">the last day</option>"
        print u"<option value=\"48.0\" selected=\"selected\">the last 2 days</option>"
        print u"<option value=\"168.0\" selected=\"selected\">the last week</option>"
    print u"</select>"

    print u" for device "
    print u"<select name=\"deviceid\">"
    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()
        cmd = u"Select device, friendly_name from devices order by friendly_name"
        rows = curs.execute(cmd)
        for row in rows:
            if deviceid == row[0]:
                print u"<option value=\"{0}\" selected=\"selected\">{1}</option>".format(row[0], row[1])
            else:
                print u"<option value=\"{0}\">{1}</option>".format(row[0], row[1])
    print u"</select>"

    print u" in database "
    print u"<select name=\"dbname\">"
    for name in dbnames:
        if name == dbname:
            print u"<option value=\"{0}\" selected=\"selected\">{1}</option>".format(name, name)
        else:
            print u"<option value=\"{0}\">{1}</option>".format(name, name)
    print u"</select>"

    print u"<input type=\"submit\" value=\"Display\">"
    print u"</form>"


#return the hours passed to the script
def get_hours():
    hours = unicode(24)
    if form.getvalue(u'hours'):
        hours = form.getvalue(u'hours')
        if hours is None:
            hours = unicode(24)
    return float(hours)


#returns dbname
def get_dbname(dbnames):
    dbname = 'no database'
    if form.getvalue(u'dbname'):
        dbname = form.getvalue(u'dbname')
        if dbname in dbnames:
            return dbname
    if dbnames == None or len(dbnames) == 0:
        dbname = 'No databases found'
    else:
        dbname = dbnames[len(dbnames) - 1]
    return dbname


#return the tdevice passed to the script
def get_tdevice():
    global dbfile
    if form.getvalue(u'deviceid'):
        deviceid = form.getvalue(u'deviceid')
        cmd = u"Select device, friendly_name, device_type from devices where device = '{0}' limit 1".format(deviceid)
        with sqlite3.connect(dbfile) as conn:
            curs = conn.cursor()
            rows = curs.execute(cmd)
            if rows != None:
                for row in rows:
                    deviceid = row[0]
                    friendly_name = row[1]
                    device_type = row[2]
                    return deviceid, friendly_name, device_type
    #print "cmd=",cmd                                                               #debugging
    cmd = u"Select device, friendly_name, device_type from devices order by friendly_name"  #default to the last one, first one will be a number!.
    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()
        rows = curs.execute(cmd)
        for row in rows:
            deviceid = row[0]
            friendly_name = row[1]
            device_type = row[2]
            # if friendly_name == 'waterheater':
        # return deviceid, friendly_name, device_type  #testing without putting in parameters
        return deviceid, friendly_name, device_type


def get_endtime(tdevice, hours):
    # endstamp = rows[0][0]
    # startstamp = rows[len(rows)-1][0]
    # endtime=date2num(datetime.datetime.strptime( endstamp, u"%Y-%m-%d %H:%M:%S.%f"))
    # starttime=date2num(datetime.datetime.strptime(startstamp, u"%Y-%m-%d %H:%M:%S.%f"))
    # actualtimespan=endtime-starttime

    endtime = None
    if form.getvalue(u'endtime'):
        try:
            stringendtime = form.getvalue(u'endtime')
            if stringendtime == u'now':
                endtime = None
            endtime = dparser.parse(stringendtime)
            endtime = datetime.datetime.strptime(endtime, u"%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            endtime = None
            logger.debug('Value error parsing form endtime')
    if endtime == None:
        endstamp = get_lastlogtime(tdevice)
        endtime = datetime.datetime.strptime(endstamp, u"%Y-%m-%d %H:%M:%S.%f")
    hrs = float(hours)
    tdelta = datetime.timedelta(hours=hrs)
    starttime = endtime - tdelta
    return starttime, endtime


def get_lastlogtime(tdevice):
    global dbfile
    cmd = u"Select timestamp from temperatures where device = '{0}' order by timestamp desc limit 1".format(tdevice[0])
    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()
        rows = curs.execute(cmd)
        for row in rows:
            lastlogtime = row[0]
            return lastlogtime


# make the tlogx standard date time display string, input must not have the tz data
def displaydatetime(string_date):
    dt = datetime.datetime.strptime(string_date, u"%Y-%m-%d %H:%M:%S.%f")
    return u"{0:%m-%d %H}:{0:%M}:{0:%S}".format(dt)


# main function
# This is where the program starts
def main():
    global dbfile

    #enable debugging
    cgitb.enable()

    #setup main constant variables
    dbpath, dbnames = get_dbnames()

    # print the HTTP header
    printHTTPheader()

    # get options that may have been passed to this script
    dbname = get_dbname(dbnames)
    dbfile = os.path.join(dbpath, dbname)
    logger.debug('using database=' + dbfile)
    tdevice = get_tdevice()
    logger.debug('tdevice={0}'.format(tdevice))
    hours = get_hours()
    logger.debug('hours=' + str(hours))
    starttime, endtime = get_endtime(tdevice, hours)  #gets endtime from input or last db entry for device
    logger.debug(
        'starttime=' + starttime.strftime("%Y-%m-%d %H:%M:%S") + ', endtime=' + endtime.strftime("%Y-%m-%d %H:%M:%S"))

    # get data from the database
    dates, temperatures, mintempdate, mintemp, maxtempdate, maxtemp, avgtemp = get_tdata(tdevice[0], starttime, endtime)

    heatingdegreedays = get_degree_days('28-00044b5468ff', '28-0004612af9ff', starttime,
                                        endtime)  # inside, outside, starttime, endtime

    starttime = num2date(dates[0])  # adjust dates to actual
    endtime = num2date(dates[len(dates) - 1])

    if len(dates) > 2:
        # convert the data into a table
        heaterontime, heaterdates, heateronpoints = getheaterontime(dates, temperatures, tdevice[2])
        table = create_table(dates, temperatures, heaterdates, heateronpoints)
    else:
        print u"No data found"
        return


    # start printing the page
    print u"<html>"
    # print the head section including the table
    # used by the javascript for the chart
    printHTMLHead(u"Hallocks Temperature Log", table)

    # print the page body
    print u"<body>"
    print u"<h1>Hallocks Temperature Log</h1>"
    print u"<hr>"
    print_options_selector(dbname, tdevice[0], hours, dbnames)
    print u"<img src='../tchart.png'>"

    show_graph_title(starttime, endtime, tdevice)

    show_stats(dates, temperatures, str(num2date(mintempdate))[:-6], mintemp, str(num2date(maxtempdate))[:-6], maxtemp,
               avgtemp, starttime, endtime, heaterontime, tdevice, heatingdegreedays)
    print u"</body>"
    print u"</html>"

    sys.stdout.flush()


if __name__ == u"__main__":
    main()


