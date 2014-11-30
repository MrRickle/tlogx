#!/usr/bin/env python2

#this file gets copied to /var/www  (eventualy it should be the cgi-bin folder)


from __future__ import division
from __future__ import with_statement
import datetime
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange, date2num
from pylab import savefig
from optparse import OptionParser
import sqlite3
import sys
import cgi
import cgitb
import io
from matplotlib.ticker import MultipleLocator, FormatStrFormatter


# global variables
speriod=(15*60)-1
dbname=u'./data/tlog.db'
#cgibinFolder = u''   #set here so I can test with source code
form = cgi.FieldStorage()

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
def get_tdata(interval,device_id):
    #print 'device_id =',device_id                                              #debugging
    now = get_lastlogtime()
    dates = []
    temperatures = []
    mindate = 0
    maxdate = 0
    mintemp = 0
    maxtemp = 0


    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        cmd = u"SELECT  min(timestamp), max(timestamp), min (temperature), max(temperature) FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}') order by timestamp desc limit 200".format(device_id,now,interval)
        curs.execute(cmd)
        row = curs.fetchone()
        mindate = date2num( datetime.datetime.strptime(row[0], u"%Y-%m-%d %H:%M:%S.%f"))
        maxdate = date2num( datetime.datetime.strptime(row[1], u"%Y-%m-%d %H:%M:%S.%f"))
        mintemp = float(row[2])
        maxtemp = float(row[3])

        cmd = u"SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}') order by timestamp desc limit 200".format(device_id,now,interval)
        curs.execute(cmd)
        rows=curs.fetchall()
        for row in rows:
            dt =date2num(datetime.datetime.strptime(row[0], u"%Y-%m-%d %H:%M:%S.%f"))
            dates.append(dt)
            temperatures.append(float(row[1]))

    return dates,temperatures,mindate,maxdate,mintemp,maxtemp


# convert rows from database into a javascript table
def create_table(dates,temperatures, mindate, maxdate, mintemp, maxtemp):

    # majorLocator   = MultipleLocator((maxdate-mindate)/20)
    # majorFormatter = FormatStrFormatter('%D')
    # minorLocator   = MultipleLocator((maxdate-mindate)/5)

    fig, ax = plt.subplots()
    ax.plot_date(dates, temperatures, u'-')
    ax.autoscale_view()
    # ax.xaxis.set_major_locator(majorLocator)
    # ax.xaxis.set_major_formatter(majorFormatter)
    #
    # #for the minor ticks, use no labels; default NullFormatter
    # ax.xaxis.set_minor_locator(minorLocator)

    ax.grid(True)

    fig.autofmt_xdate()
    savefig(u'tchart.png', bbox_inches=u'tight')
# # Save the image to buffer
# buf = io.BytesIO()
# fig.savefig(buf, format='png')
# out = buf.getvalue()
# buf.close()
# print ('Content-Type: image/png\n')
# print (out)





# print the javascript to generate the chart
# pass the table generated from the database info
def print_graph_script(table):

    # google chart snippet
    chart_code=u"""
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load("visualization", "1", {packages:["corechart"]});
      google.setOnLoadCallback(drawChart);
      function drawChart() {
        var data = google.visualization.arrayToDataTable([['Time', 'Temperature'],%s]);
        var options = {title: 'Temperature'};
        var chart = new google.visualization.ScatterChart(document.getElementById('chart_div'));
        chart.draw(data, options);
      }
    </script>"""

    print chart_code % (table)




# print the div that contains the graph
def show_graph(timeinterval, tdevice):
    print u"<h2>Temperature Chart for the last {0} hours for device {2} (id={1})</h2>".format(timeinterval,tdevice[0],tdevice[1])
    print u'<div id="chart_div" style="width: 1500px; height: 500px;"></div>'



# connect to the db and show some stats
# argument option is the number of hours
def show_stats(timeinterval,tdevice):
    now = get_lastlogtime()
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()

        if timeinterval is None:
            timeinterval = unicode(24)

        cmd=u"SELECT timestamp, max(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0], now, timeinterval)
        curs.execute(cmd)
        rowmax=curs.fetchone()
        if rowmax is None:
            rowstrmax =u'NA'
        else:
            rowstrmax=u"{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowmax[0]),rowmax[1], rowmax[1]*5/9+32)

        cmd=u"SELECT timestamp, min(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0], now, timeinterval)
        curs.execute(cmd)
        rowmin=curs.fetchone()
        if rowmax is None:
            rowstrmin =u'NA'
        else:
            rowstrmin=u"{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowmin[0]),rowmin[1], rowmin[1]*5/9+32)

        cmd=u"SELECT timestamp, avg(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0], now, timeinterval)
        curs.execute(cmd)
        rowavg=curs.fetchone()
        if rowmax is None:
            rowstravg =u'NA'
        else:
            rowstravg=u"{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowavg[0]),rowavg[1], rowavg[1]*5/9+32)


        print u"<hr>"


        print u"<h2>Minumum temperature&nbsp</h2>"
        print rowstrmin
        print u"<h2>Maximum temperature</h2>"
        print rowstrmax
        print u"<h2>Average temperature</h2>"
        print rowstravg

        print u"<hr>"

        print u"<h2>Temperature Points:</h2>"
        print u"<table>"
        print u"<tr><td><strong>Date/Time</strong></td><td><strong>Temp C</strong></td><td><strong>Temp F</strong></td></tr>"

        cmd =u"SELECT timestamp, temperature FROM temperatures WHERE device = '{0}' and timestamp > datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0],now,timeinterval)
        rows=curs.execute(cmd)
        for row in rows:
            tf = float(row[1])*5/9+32
            tc = float(row[1])
            rowstr=u"<tr><td>{0}&emsp;&emsp;</td><td>{1:7.2f} C</td><td>{2:7.1f} F</td></tr>".format(unicode(row[0]),tc,tf)
            print rowstr
        print u"</table>"

        print u"<hr>"




def print_options_selector(timeinterval,deviceid):

    print u"<form action=\"twebgui.py\" method=\"POST\">"
    print u" Show the temperature logs for "  
    print u"<select name=\"timeinterval\">"
    if timeinterval is not None:
     
        if timeinterval == u"30m":
            print u"<option value=\".5\" selected=\"selected\">the last 30 minutes</option>"
        else:
            print u"<option value=\".5\">the last 30 minutes hours</option>"

        if timeinterval == u"1":
            print u"<option value=\"1\" selected=\"selected\">the last 1 hours</option>"
        else:
            print u"<option value=\"1\">the last 1 hours</option>"

        if timeinterval == u"6":
            print u"<option value=\"6\" selected=\"selected\">the last 6 hours</option>"
        else:
            print u"<option value=\"6\">the last 6 hours</option>"

        if timeinterval == u"12":
            print u"<option value=\"12\" selected=\"selected\">the last 12 hours</option>"
        else:
            print u"<option value=\"12\">the last 12 hours</option>"

        if timeinterval == u"24":
            print u"<option value=\"24\" selected=\"selected\">the last 24 hours</option>"
        else:
            print u"<option value=\"24\">the last 24 hours</option>"

    else:
        print u"<option value=\".5\">the last 30 minutes</option>"
        print u"<option value=\"1\">the last 1 hour</option>"
        print u"<option value=\"6\">the last 6 hours</option>"
        print u"<option value=\"12\">the last 12 hours</option>"
        print u"<option value=\"24\" selected=\"selected\">the last 24 hours</option>"
    print u"</select>"
    
    print u" for device "
    
    print u"<select name=\"deviceid\">"
    with sqlite3.connect(dbname) as conn:
        curs = conn.cursor()
        cmd = u"Select device, friendly_name from devices"
        rows = curs.execute(cmd)
        for row in rows:
            if deviceid == row[0]:
                print u"<option value=\"{0}\" selected=\"selected\">{1}</option>".format(row[0], row[1])
            else:
                print u"<option value=\"{0}\">{1}</option>".format(row[0],row[1])
    print u"</select>"
    print u"<input type=\"submit\" value=\"Display\">"
    print u"</form>"


#return the option passed to the script
def get_timeinterval():
    timeinterval = unicode(24)
    if form.getvalue(u'timeinterval'):
        timeinterval = form.getvalue(u'timeinterval')
        if timeinterval is None:
            timeinterval = unicode(24)
    return timeinterval

def get_lastlogtime():
    cmd = u"Select timestamp from temperatures order by timestamp desc limit 1"
    with sqlite3.connect(dbname) as conn:
        curs = conn.cursor()
        rows = curs.execute(cmd)
        for row in rows:
            lastlogtime = row[0]
            return lastlogtime
    

#return the tdevice passed to the script
def get_tdevice():
    cmd = u"Select device, friendly_name from devices order by friendly_name limit 1"
    if form.getvalue(u'deviceid'):
        deviceid = form.getvalue(u'deviceid')
        cmd = u"Select device, friendly_name from devices where device = '{0}' limit 1".format(deviceid)
    #print "cmd=",cmd                                                               #debugging
    with sqlite3.connect(dbname) as conn:
        curs = conn.cursor()
        rows = curs.execute(cmd)
        for row in rows:
            deviceid = row[0]
            friendly_name = row[1] 
            return deviceid,friendly_name
        
# make the tlogx standard date time display string
def displaydatetime(string_date):
    dt =datetime.datetime.strptime(string_date, u"%Y-%m-%d %H:%M:%S.%f")
    return u"{0:%m-%d %H}:{0:%M}:{0:%S}".format(dt)    

# main function
# This is where the program starts 
def main():
    #enable debugging
    cgitb.enable()

    # print the HTTP header
    printHTTPheader()

    #print form.getvalue('timeinterval'),form.getvalue('deviceid')               #debugging

    # get options that may have been passed to this script
    timeinterval = get_timeinterval()
    #print "timeinterval",timeinterval                                           #debugging
    tdevice = get_tdevice()
    #print "tdevice", tdevice                                                   #debugging

    # get data from the database
    dates, temperatures, mindate, maxdate, mintemp, maxtemp = get_tdata(timeinterval,tdevice[0])

    if len(dates) > 2:
        # convert the data into a table
        table=create_table(dates,temperatures, mindate, maxdate, mintemp, maxtemp )
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
    print_options_selector(timeinterval,tdevice[0])
    print u"<img src='tchart.png'>"

    show_graph(timeinterval, tdevice)
    show_stats(timeinterval, tdevice)
    print u"</body>"
    print u"</html>"

    sys.stdout.flush()

if __name__==u"__main__":
    main()




