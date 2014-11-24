import datetime
#!/usr/bin/env python

import sqlite3
import sys
import cgi
import cgitb


# global variables
speriod=(15*60)-1
dbname='./data/tlog.db'


# print the HTTP header
def printHTTPheader():
    print "Content-type: text/html\n\n"


# print the HTML head section
# arguments are the page title and the table for the chart
def printHTMLHead(title, table):
    print "<head>"
    print "    <title>"
    print title
    print "    </title>"
    
    print_graph_script(table)

    print "</head>"


# get data from the database
# if an interval is passed, 
# return a list of records from the database
def get_data(interval):
    device = '28-Device0'  #change to an input
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        if interval == None:
            cmd = "SELECT timestamp, temperature FROM  temperatures  where device = '{0}'".format(device)
            curs.execute(cmd)
        else:
#           now = datetime.datetime.now
            now = '2014-11-23 15:59:28.628628'
            cmd = "SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device,now,interval) 
            curs.execute(cmd)

    rows=curs.fetchall()

    conn.close()

    return rows


# convert rows from database into a javascript table
def create_table(rows):
    chart_table=""

    for row in rows[:-1]:
        rowstr="['{0}', {1}],\n".format(str(row[0]),str(row[1]))
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
        var data = google.visualization.arrayToDataTable([
          ['Time', 'Temperature'],
%s
        ]);

        var options = {
          title: 'Temperature'
        };

        var chart = new google.visualization.LineChart(document.getElementById('chart_div'));
        chart.draw(data, options);
      }
    </script>"""

    print chart_code % (table)




# print the div that contains the graph
def show_graph():
    print "<h2>Temperature Chart</h2>"
    print '<div id="chart_div" style="width: 900px; height: 500px;"></div>'



# connect to the db and show some stats
# argument option is the number of hours
def show_stats(option):
    device = '28-Device0'
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()

        if option is None:
            option = str(24)
#       now = datetime.datetime.now
        now = '2014-11-23 15:59:28.628628'

        cmd="SELECT timestamp, max(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(device, now, option)
        curs.execute(cmd)
        rowmax=curs.fetchone()
        rowstrmax="{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowmax[0]),rowmax[1], rowmax[1]*5/9+32)

        cmd="SELECT timestamp, min(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(device, now, option)
        curs.execute(cmd)
        rowmin=curs.fetchone()
        rowstrmin="{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowmin[0]),rowmin[1], rowmin[1]*5/9+32)

        cmd="SELECT timestamp, avg(temperature) FROM temperatures WHERE device = '{0}' and timestamp>datetime('{1}','-{2} hour') AND timestamp<=datetime('{1}')".format(device, now, option)
        curs.execute(cmd)
        rowavg=curs.fetchone()
        rowstravg="{0}&nbsp&nbsp&nbsp{1:6.2f} C {2:6.1f} F".format(displaydatetime(rowavg[0]),rowavg[1], rowavg[1]*5/9+32)


        print "<hr>"


        print "<h2>Minumum temperature&nbsp</h2>"
        print rowstrmin
        print "<h2>Maximum temperature</h2>"
        print rowstrmax
        print "<h2>Average temperature</h2>"
        print rowstravg

        print "<hr>"

        print "<h2>In the last hour:</h2>"
        print "<table>"
        print "<tr><td><strong>Date/Time</strong></td><td><strong>Temperature</strong></td></tr>"

        cmd ="SELECT * FROM temperatures WHERE device = '{0}' and timestamp > datetime('{1}','-1 hour') AND timestamp<=datetime('{1}')".format(device,now)
        rows=curs.execute(cmd)
        for row in rows:
            rowstr="<tr><td>{0}&emsp;&emsp;</td><td>{1}C</td></tr>".format(str(row[0]),str(row[1]))
            print rowstr
        print "</table>"

        print "<hr>"




def print_time_selector(option):

    print """<form action="/cgi-bin/webgui.py" method="POST">
        Show the temperature logs for  
        <select name="timeinterval">"""


    if option is not None:

        if option == "6":
            print "<option value=\"6\" selected=\"selected\">the last 6 hours</option>"
        else:
            print "<option value=\"6\">the last 6 hours</option>"

        if option == "12":
            print "<option value=\"12\" selected=\"selected\">the last 12 hours</option>"
        else:
            print "<option value=\"12\">the last 12 hours</option>"

        if option == "24":
            print "<option value=\"24\" selected=\"selected\">the last 24 hours</option>"
        else:
            print "<option value=\"24\">the last 24 hours</option>"

    else:
        print """<option value="6">the last 6 hours</option>
            <option value="12">the last 12 hours</option>
            <option value="24" selected="selected">the last 24 hours</option>"""

    print """        </select>
        <input type="submit" value="Display">
    </form>"""


# check that the option is valid
# and not an SQL injection
def validate_input(option_str):
    # check that the option string represents a number
    if option_str.isalnum():
        # check that the option is within a specific range
        if int(option_str) > 0 and int(option_str) <= 24:
            return option_str
        else:
            return None
    else: 
        return None


#return the option passed to the script
def get_option():
    form=cgi.FieldStorage()
    if "timeinterval" in form:
        option = form["timeinterval"].value
        return validate_input (option)
    else:
        return None
# make the tlogx standard date time display string
def displaydatetime(string_date):
    dt =datetime.datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S.%f")
    return "{0:%m-%d %H}:{0:%M}:{0:%S}".format(dt)
    

# main function
# This is where the program starts 
def main():

    cgitb.enable()

    # get options that may have been passed to this script
    option=get_option()

    if option is None:
        option = str(24)

    # get data from the database
    records=get_data(option)

    # print the HTTP header
    printHTTPheader()

    if len(records) != 0:
        # convert the data into a table
        table=create_table(records)
    else:
        print "No data found"
        return

    # start printing the page
    print "<html>"
    # print the head section including the table
    # used by the javascript for the chart
    printHTMLHead("Raspberry Pi Temperature Logger", table)

    # print the page body
    print "<body>"
    print "<h1>Raspberry Pi Temperature Logger</h1>"
    print "<hr>"
    print_time_selector(option)
    show_graph()
    show_stats(option)
    print "</body>"
    print "</html>"

    sys.stdout.flush()

if __name__=="__main__":
    main()




