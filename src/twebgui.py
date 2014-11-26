#!/usr/bin/env python

import datetime

import sqlite3
import sys
import cgi
import cgitb


# global variables
speriod=(15*60)-1
dbname='./data/tlog.db'
cgibinFolder = ''   #set here so I can test with source code
form = cgi.FieldStorage()

# print the HTTP header
def printHTTPheader():
    print("Content-type: text/html\n\n")


# print the HTML head section
# arguments are the page title and the table for the chart
def printHTMLHead(title, table):
    print("<head>")
    print("    <title>")
    print(title)
    print("    </title>")
    
    print_graph_script(table)

    print("</head>")


# get data from the database
# if an interval is passed, 
# return a list of records from the database
def get_tdata(interval,device_id):
    #print 'device_id =',device_id                                              #debugging
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        now = str(datetime.datetime.now())
        cmd = "SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device_id,now,interval) 
       #cmd = "SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device_id,now,interval) 
       #cmd = "SELECT strftime('%d %H:%M:%S',timestamp), temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device_id,now,interval) 
        curs.execute(cmd)
    rows=curs.fetchall()
    conn.close()
    newrows=[]
    for row in rows:
        dt =datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
        epoch = (dt- datetime.datetime(1970,1,1)).total_seconds()
        temperature = row[1]
        newrow = epoch,temperature
        newrows.append(newrow)
    return newrows


# convert rows from database into a javascript table
def create_table(rows):
    chart_table=""

    for row in rows[:-1]:
        rowstr="[{0}, {1}],\n".format(row[0],row[1])
        chart_table+=rowstr

    row=rows[-1]
    rowstr="['{0}', {1}]\n".format(str(row[0]),str(row[1]))
    chart_table+=rowstr

    return chart_table


# print the javascript to generate the chart
# pass the table generated from the database info
def print_graph_script(table):

    # google chart snippet
    chart_code="""
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

    print(chart_code % (table))




# print the div that contains the graph
def show_graph(timeinterval, tdevice):
    print("<h2>Temperature Chart for the last {0} hours for device {2} (id={1})</h2>".format(timeinterval,tdevice[0],tdevice[1]))
    print('<div id="chart_div" style="width: 1500px; height: 500px;"></div>')



# connect to the db and show some stats
# argument option is the number of hours
def show_stats(timeinterval,tdevice):
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()

        if timeinterval is None:
            timeinterval = str(24)
        now = datetime.datetime.now()

        cmd="SELECT timestamp, max(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0], now, timeinterval)
        curs.execute(cmd)
        rowmax=curs.fetchone()
        if rowmax is None:
            rowstrmax ='NA'
        else:
            rowstrmax="{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowmax[0]),rowmax[1], rowmax[1]*5/9+32)

        cmd="SELECT timestamp, min(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0], now, timeinterval)
        curs.execute(cmd)
        rowmin=curs.fetchone()
        if rowmax is None:
            rowstrmin ='NA'
        else:
            rowstrmin="{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowmin[0]),rowmin[1], rowmin[1]*5/9+32)

        cmd="SELECT timestamp, avg(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0], now, timeinterval)
        curs.execute(cmd)
        rowavg=curs.fetchone()
        if rowmax is None:
            rowstravg ='NA'
        else:
            rowstravg="{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowavg[0]),rowavg[1], rowavg[1]*5/9+32)


        print("<hr>")


        print("<h2>Minumum temperature&nbsp</h2>")
        print(rowstrmin)
        print("<h2>Maximum temperature</h2>")
        print(rowstrmax)
        print("<h2>Average temperature</h2>")
        print(rowstravg)

        print("<hr>")

        print("<h2>Temperature Points:</h2>")
        print("<table>")
        print("<tr><td><strong>Date/Time</strong></td><td><strong>Temp C</strong></td><td><strong>Temp F</strong></td></tr>")

        cmd ="SELECT timestamp, temperature FROM temperatures WHERE device = '{0}' and timestamp > datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(tdevice[0],now,timeinterval)
        rows=curs.execute(cmd)
        for row in rows:
            tf = float(row[1])*5/9+32
            tc = float(row[1])
            rowstr="<tr><td>{0}&emsp;&emsp;</td><td>{1:7.2f} C</td><td>{2:7.1f} F</td></tr>".format(str(row[0]),tc,tf)
            print(rowstr)
        print("</table>")

        print("<hr>")




def print_options_selector(timeinterval,deviceid):

    print("<form action=\"twebgui.py\" method=\"POST\">")
    print(" Show the temperature logs for ")  
    print("<select name=\"timeinterval\">")
    if timeinterval is not None:
     
        if timeinterval == "30m":
            print("<option value=\".5\" selected=\"selected\">the last 30 minutes</option>")
        else:
            print("<option value=\".5\">the last 30 minutes hours</option>")

        if timeinterval == "1":
            print("<option value=\"1\" selected=\"selected\">the last 1 hours</option>")
        else:
            print("<option value=\"1\">the last 1 hours</option>")

        if timeinterval == "6":
            print("<option value=\"6\" selected=\"selected\">the last 6 hours</option>")
        else:
            print("<option value=\"6\">the last 6 hours</option>")

        if timeinterval == "12":
            print("<option value=\"12\" selected=\"selected\">the last 12 hours</option>")
        else:
            print("<option value=\"12\">the last 12 hours</option>")

        if timeinterval == "24":
            print("<option value=\"24\" selected=\"selected\">the last 24 hours</option>")
        else:
            print("<option value=\"24\">the last 24 hours</option>")

    else:
        print("<option value=\".5\">the last 30 minutes</option>")
        print("<option value=\"1\">the last 1 hour</option>")
        print("<option value=\"6\">the last 6 hours</option>")
        print("<option value=\"12\">the last 12 hours</option>")
        print("<option value=\"24\" selected=\"selected\">the last 24 hours</option>")
    print("</select>")
    
    print(" for device ")
    
    print("<select name=\"deviceid\">")
    with sqlite3.connect(dbname) as conn:
        curs = conn.cursor()
        cmd = "Select device, friendly_name from devices"
        rows = curs.execute(cmd)
        for row in rows:
            if deviceid == row[0]:
                print("<option value=\"{0}\" selected=\"selected\">{1}</option>".format(row[0], row[1]))
            else:
                print("<option value=\"{0}\">{1}</option>".format(row[0],row[1]))
    print("</select>")
    print("<input type=\"submit\" value=\"Display\">")
    print("</form>")


#return the option passed to the script
def get_timeinterval():
    timeinterval = str(24)
    if form.getvalue('timeinterval'):
        timeinterval = form.getvalue('timeinterval')
        if timeinterval is None:
            timeinterval = str(24)
    return timeinterval
    

#return the tdevice passed to the script
def get_tdevice():
    cmd = "Select device, friendly_name from devices order by friendly_name limit 1"
    if form.getvalue('deviceid'):
        deviceid = form.getvalue('deviceid')
        cmd = "Select device, friendly_name from devices where device = '{0}' limit 1".format(deviceid)
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
    dt =datetime.datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S.%f")
    return "{0:%m-%d %H}:{0:%M}:{0:%S}".format(dt)    

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
    records=get_tdata(timeinterval,tdevice[0])

    if len(records) != 0:
        # convert the data into a table
        table=create_table(records)
    else:
        print("No data found")
        return
    

    # start printing the page
    print("<html>")
    # print the head section including the table
    # used by the javascript for the chart
    printHTMLHead("Raspberry Pi Temperature Logger", table)

    # print the page body
    print("<body>")
    print("<h1>Raspberry Pi Temperature Logger</h1>")
    print("<hr>")
    print_options_selector(timeinterval,tdevice[0])
    show_graph(timeinterval, tdevice)
    show_stats(timeinterval, tdevice)
    print("</body>")
    print("</html>")

    sys.stdout.flush()

if __name__=="__main__":
    main()




