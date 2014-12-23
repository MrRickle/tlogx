#!/home/rickldftp/anaconda/bin/python
#!/home/rick/anaconda3/envs/py278/bin/python
#!/C:Users\Rick\Anaconda\bin\python


#this file gets copied to /var/www  (eventualy it should be the cgi-bin folder)


from __future__ import division
from __future__ import with_statement
import datetime
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange, date2num, num2date
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
speriod=(15*60)-1
dbfile = None

form = cgi.FieldStorage()

#gets the database path and list of database names in it.
def get_dbnames():
    logger.debug("getting dblist")
    dbfiles = sorted(glob.glob(u'../tlogx/data/*.db'))
    if dbfiles == None or len(dbfiles)==0:
        dbfiles = sorted(glob.glob(u'*.db'))
    # search for a devices file that start with 28
    if dbfiles==[]:
        logger.critical( u'no databases found')
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
def get_tdata(tdevice, starttime, endtime):
    global dbfile
    temperatures = []
    mintemp = 100
    maxtemp = -100
    mintempdate = sys.float_info.max
    maxtempdate = 0;


    with sqlite3.connect(dbfile) as conn:
        curs=conn.cursor()

        cmd = u"SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>=datetime('{1}') AND timestamp<=datetime('{2}') order by timestamp desc limit 10000".format(tdevice[0],starttime,endtime)
        curs.execute(cmd)
        rows=curs.fetchall()
        dates = []
        for row in rows:
            dt = date2num(datetime.datetime.strptime(row[0], u"%Y-%m-%d %H:%M:%S.%f"))
            dates.append(dt)
            temp=float(row[1])
            temperatures.append(temp)
            if mintemp>temp:
                mintemp=temp
                mintempdate=dt
            if maxtemp<temp:
                maxtemp=temp
                maxtempdate=dt
        avgtemp = "NA"

    return dates, temperatures, mintempdate, mintemp, maxtempdate, maxtemp, avgtemp



# convert rows from database into a javascript table
def create_table(dates,temperatures):
    def Tf(Tc):
        return (Tc*9./5.)+32
    def update_ax2(ax):
        y1, y2 = ax.get_ylim()
        ax2.set_ylim(Tf(y1), Tf(y2))
        ax2.figure.canvas.draw()

    # majorLocator   = MultipleLocator((maxdate-mindate)/20)
    # majorFormatter = FormatStrFormatter('%D')
    # minorLocator   = MultipleLocator((maxdate-mindate)/5)

    fig, ax = plt.subplots() #ax is the Celsius scale
    ax2 = ax.twinx()         #ax2 is the Fahrenheit scale
    ax.callbacks.connect("ylim_changed", update_ax2)
    ax.plot_date(dates, temperatures, u'-')
    ax.autoscale_view()
    # ax.xaxis.set_major_locator(majorLocator)
    # ax.xaxis.set_major_formatter(majorFormatter)

    #for the minor ticks, use no labels; default NullFormatter
    # ax.xaxis.set_minor_locator(minorLocator)

    ax.grid(True)

    fig.autofmt_xdate()
    savefig(u'../tchart.png', bbox_inches=u'tight')
# # Save the image to buffer
    #buf = io.BytesIO()
    #fig.savefig(buf, format='png')
    #out = buf.getvalue()
    #buf.close()
    #print ('Content-Type: image/png\n')
    #print (out)


def getfurnaceontime(dates, temperatures, device_type):
    if device_type != 'furnace':
        return ''
    furnaceonslope = 4000 #slope that says furnace has started. deg/day
    furnaceoffslope = -400 #slope that says furnace has stopped.
    furnaceontime = float(0)
    furnaceison = False
    for i in reversed(range(0,len(dates)-1)): # note we have sorted dates in descending order so newest is at the top.
        tdelta = temperatures[i]-temperatures[i+1]
        ddelta = dates[i]-dates[i+1]
        slope = tdelta/ddelta
        if furnaceison:
            if (slope < furnaceoffslope):
                furnaceison=False
        else:
            if (slope>furnaceonslope):   #add more conditions so we get the time after furnace is as hot as it gets.
                furnaceison=True
        if furnaceison:
            furnaceontime = furnaceontime + ddelta
    percent = int (furnaceontime / (dates[0]-dates[len(dates)-1])*100)

    total_seconds = int(furnaceontime*24*60*60)
    hours, remainder = divmod(total_seconds,60*60)
    minutes, seconds = divmod(remainder,60)
    hours ='{0:02.0f}:{1:02.0f}:{2:02.0f}'.format(hours,minutes,seconds)
    return  "Furnace on time = "+hours+ ", "+str(percent)+"%"


def timedeltatostring (timedelta):
    totalleft = timedelta*24
    hours = int (totalleft)
    totalleft = (totalleft-hours)*60
    minutes = int(totalleft)
    totalleft = (totalleft-minutes)*60
    seconds = int(totalleft)
    str = "{0:02.0f}:{1:02.0f}:{2:02.0f}".format(hours, minutes, seconds)
    return str

# print the div that contains the graph
def show_graph_title(starttime, endtime, tdevice):
    hours = (endtime - starttime).total_seconds()/3600
    print u"<h2>Temperature Chart from {0} to {1} ({2:.0f} hours) for {4} (deviceid={3})</h2>".format((str(starttime))[:-10], (str(endtime))[:-10], hours, tdevice[0], tdevice[1])
    print u'<div id="chart_div" style="width: 1500px; height: 100px;"></div>'


# connect to the db and show some stats
# argument option is the number of hours
def show_stats(dates, temperatures, mindate, mintemp, maxdate, maxtemp, avgtemp, starttime, endtime, furnacestr, tdevice):

    rowstrmax=u"{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(maxdate),maxtemp, maxtemp*9/5+32)
    rowstrmin=u"{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(mindate),mintemp, mintemp*9/5+32)

    if furnacestr != '':
        print u"<hr>"
        print u"<h2>" + furnacestr + "</h2>"

    print u"<hr>"
    print u"<h2>Minumum temperature&nbsp</h2>"
    print rowstrmin
    print u"<h2>Maximum temperature</h2>"
    print rowstrmax
    print u"<hr>"

    print u"<h2>Temperature Points:</h2>"
    print u"<table>"
    print u"<tr><td><strong>Date/Time</strong></td><td><strong>Temp C</strong></td><td><strong>Temp F</strong></td></tr>"

    for i in range (0, len(dates)):
        tf = float(temperatures[i])*9/5+32
        tc = float(temperatures[i])
        rowstr=u"<tr><td>{0}&emsp;&emsp;</td><td>{1:7.2f} C</td><td>{2:7.1f} F</td></tr>".format(displaydatetime(str(num2date(dates[i]))[:-6]),tc,tf)
        print rowstr
    print u"</table>"
    print u"<hr>"




def print_options_selector(dbname, deviceid, hours, dbnames):

    print u"<form action=\"twebgui.py\" method=\"POST\">"
    print u" Show the temperature logs for "
    print u"<select name=\"hours\">"
    if hours is not None:

        if hours == u"30m":
            print u"<option value=\".5\" selected=\"selected\">the last 30 minutes</option>"
        else:
            print u"<option value=\".5\">the last 30 minutes hours</option>"

        if hours == u"1":
            print u"<option value=\"1\" selected=\"selected\">the last 1 hours</option>"
        else:
            print u"<option value=\"1\">the last 1 hours</option>"

        if hours == u"6":
            print u"<option value=\"6\" selected=\"selected\">the last 6 hours</option>"
        else:
            print u"<option value=\"6\">the last 6 hours</option>"

        if hours == u"12":
            print u"<option value=\"12\" selected=\"selected\">the last 12 hours</option>"
        else:
            print u"<option value=\"12\">the last 12 hours</option>"

        if hours == u"24":
            print u"<option value=\"24\" selected=\"selected\">the last 24 hours</option>"
        else:
            print u"<option value=\"24\">the last 24 hours</option>"
        if hours == u"48":
            print u"<option value=\"48\" selected=\"selected\">the last 48 hours</option>"
        else:
            print u"<option value=\"48\">the last 48 hours</option>"

        ti = int(hours)
	if ti>169:
	    ti=169
	if ti<0:
	    ti=1
        strti = '{0:03.1f}'.format(ti)
        if (ti > 0) and (ti < 169):
            print u"<option value=\""+strti+"\"selected=\"selected\">the last "+strti+" hours</option>"



    else:
        print u"<option value=\".5\">the last 30 minutes</option>"
        print u"<option value=\"1\">the last 1 hour</option>"
        print u"<option value=\"6\">the last 6 hours</option>"
        print u"<option value=\"12\">the last 12 hours</option>"
        print u"<option value=\"24\" selected=\"selected\">the last 24 hours</option>"
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
                print u"<option value=\"{0}\">{1}</option>".format(row[0],row[1])
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
    return hours

#returns dbname
def get_dbname(dbnames):
    dbname = 'no database'
    if form.getvalue(u'dbname'):
        dbname = form.getvalue(u'dbname')
        if dbname in dbnames:
            return dbname
    if dbnames == None or len(dbnames)==0:
        dbname = 'No databases found'
    else:
        dbname = dbnames[len(dbnames)-1]
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
                    return deviceid,friendly_name, device_type
    #print "cmd=",cmd                                                               #debugging
    cmd = u"Select device, friendly_name, device_type from devices order by friendly_name" #default to the last one, first one will be a number!.
    with sqlite3.connect(dbfile) as conn:
        curs = conn.cursor()
        rows = curs.execute(cmd)
        for row in rows:
            deviceid = row[0]
            friendly_name = row[1]
            device_type = row[2]
            if friendly_name == 'furnace':
                 return deviceid,friendly_name, device_type  #testing without putting in parameters
        return deviceid,friendly_name, device_type


def get_endtime(tdevice, hours):
        # endstamp = rows[0][0]
        # startstamp = rows[len(rows)-1][0]
        # endtime=date2num(datetime.datetime.strptime( endstamp, u"%Y-%m-%d %H:%M:%S.%f"))
        # starttime=date2num(datetime.datetime.strptime(startstamp, u"%Y-%m-%d %H:%M:%S.%f"))
        # actualtimespan=endtime-starttime

        endtime = None
        if form.getvalue(u'endtime'):
            try:
                stringendtime=form.getvalue(u'endtime')
                endtime = dparser.parse(stringendtime)
                endtime = datetime.datetime.strptime( endtime, u"%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                endtime = None
                logger.debug('Value error parsing form endtime')
        if endtime == None:
            endstamp = get_lastlogtime(tdevice)
            endtime = datetime.datetime.strptime( endstamp, u"%Y-%m-%d %H:%M:%S.%f")
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
    dt =datetime.datetime.strptime(string_date, u"%Y-%m-%d %H:%M:%S.%f")
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
    logger.debug('hours=' + hours)
    starttime, endtime = get_endtime(tdevice, hours)  #gets endtime from input or last db entry for device
    logger.debug('starttime='+starttime.strftime("%Y-%m-%d %H:%M:%S")+', endtime='+endtime.strftime("%Y-%m-%d %H:%M:%S"))

    # get data from the database
    dates, temperatures, mintempdate, mintemp, maxtempdate, maxtemp, avgtemp = get_tdata(tdevice, starttime, endtime)

    starttime = num2date(dates[len(dates)-1])  #adjust dates to actual
    endtime = num2date(dates[0])

    if len(dates) > 2:
        # convert the data into a table
        table=create_table(dates,temperatures)
        furnacestr = getfurnaceontime(dates,temperatures, tdevice[2])
    else:
        print u"No data found"
        return


    # start printing the page
    print u"<html>"
    # print the head section including the table
    # used by the javascript for the chart
    printHTMLHead(u"Raspberry Pi Temperature Logger", table)

    # print the page body
    print u"<body>"
    print u"<h1>Raspberry Pi Temperature Logger</h1>"
    print u"<hr>"
    print_options_selector(dbname, tdevice[0], hours, dbnames)
    print u"<img src='../tchart.png'>"

    show_graph_title(starttime, endtime, tdevice)
    show_stats(dates, temperatures, str(num2date(mintempdate))[:-6], mintemp, str(num2date(maxtempdate))[:-6], maxtemp, avgtemp, starttime, endtime, furnacestr, tdevice )
    print u"</body>"
    print u"</html>"

    sys.stdout.flush()

if __name__==u"__main__":
    main()


