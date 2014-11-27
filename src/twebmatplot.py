#!/usr/bin/env python

import cgi
import cgitb; cgitb.enable() # Enable for debug mode
import io
import sqlite3
import datetime

import numpy as np
from StringIO import StringIO
import matplotlib

matplotlib.use('Agg')
matplotlib.rcParams['timezone'] = 'US/Eastern'  # Replace with your favorite time zone
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# Read the data file
dbname='./data/tlog.db'
#data = np.genfromtxt( '../temp.dat', delimiter=',' )
device_id = '28-0004612af9ff'
interval = 24
with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        now = str(datetime.datetime.now())
        cmd = "SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device_id,now,interval) 
       #cmd = "SELECT timestamp, temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device_id,now,interval) 
       #cmd = "SELECT strftime('%d %H:%M:%S',timestamp), temperature FROM  temperatures  where device = '{0}' and timestamp>datetime('{1}','-{2} hours') AND timestamp<=datetime('{1}')".format(device_id,now,interval) 
        curs.execute(cmd)
rows=curs.fetchall()
conn.close()
data = np.genfromtxt(StringIO(rows))
dates = matplotlib.dates.epoch2num(data[:,0])
tempdata = row[:,1]

    # Set up the plot
fig, ax = plt.subplots(figsize=(6,5))
ax.plot_date( dates, tempdata, ls='-', color='red' )
ax.xaxis.set_major_formatter( DateFormatter( '%m/%d/%y %H:%M' ) )

# Read the number of hours argument and set xlim
arg = cgi.FieldStorage()
try:
    h = int( arg.getvalue('hrs', '-1') )
except:
    h = -1
if h > 0:
    ax.set_xlim( matplotlib.dates.epoch2num(data[-1,0]-h*3600), ax.get_xlim()[1] )

# Finish plot
ax.set_ylabel('Temperature F')
for label in ax.get_xticklabels():
    label.set_rotation(60)
plt.tight_layout()

# Save the image to buffer
buf = io.BytesIO()
fig.savefig(buf, format='png')
out = buf.getvalue()
buf.close()
print 'Content-Type: image/png\n'
print out
