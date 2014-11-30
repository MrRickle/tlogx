#!/usr/bin/env python

from __future__ import division
from __future__ import with_statement
import sqlite3

from threading import Timer,Thread,Event
import os
import time
from time import sleep
import datetime
import glob
import platform
import sys
from io import open
if platform.platform().startswith(u'Win'):
    import msvcrt
    print u'Windows'


class perpetualTimer():

   def __init__(self,t,hFunction,param):
      self.t=t
      self.hFunction = hFunction
      self.param = param
      self.thread = Timer(self.t,self.handle_function)

   def handle_function(self):
      self.hFunction(self.param)
      self.thread = Timer(self.t,self.handle_function)
      self.thread.start()

   def start(self):
      self.thread.start()

   def cancel(self):
      self.thread.cancel()


# global variables
notOnPi = True
speriod=(15*60)-1
dbname=u'./data/tlog.db'

def db_add_device(device):
    try:
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            cmd = u"INSERT INTO devices values(('"+device+u"'), ('"+device+u"'))"
            curs.execute(cmd)
            conn.commit
            return True
    except sqlite3.Error, e:
        print u"db_add_device_error %s:" % e.args[0]
        return False

def check_device(device):
    try:
        with sqlite3.connect(dbname) as conn:
            curs = conn.cursor()
            cmd = u"Select device from devices where device = '"+device+u"'"
            curs.execute(cmd)
            data = curs.fetchone()
            conn.commit()
            if data!= None:
                return True
            else:
                return db_add_device(device)
    except sqlite3.Error, e:
        print u"check_device error %s:" % e.args[0]
        return False
    

# store the temperature in the database
def log_temperature(device, temp):

    if not check_device(device):
        print u"There was problem finding the device in the database."
        return False
        
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        cmd = u"INSERT INTO temperatures values('{0}', '{1}', '{2:2.3}')".format (datetime.datetime.now(), device, temp)
        curs.execute(cmd)
        conn.commit()
        return True
    return False

# display the contents of the database for specified device
def display_data(device):

    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        cmd = u"Select * from temperatures where device = '"+device+u"'"
        for row in curs.execute(cmd):
            for value in row:
                print unicode(value),
            print u''    
        conn.commit()    



# get temperature
# returns None on error, or the temperature as a float
def get_temp(device_file):

    try:
        fileobj = open(device_file,u'r')
        lines = fileobj.readlines()
        fileobj.close()
    except:
        print (u"Exception opening "+devicefile)
        return None

    # get the status from the end of line 1 
    status = lines[0][-4:-1]

    # is the status is ok, get the temperature from line 2
    if status==u"YES":
        tempstr= lines[1].split(u"t=",1)[-1]
        tempvalue=float(tempstr)/1000
        return tempvalue
    else:
        print u"There was an error getting the temperature from " + devicefile+u" status="+status
        return None
    
    #do the actual logging of the temperature    

#returns device, friendly_name, temperature_check_interval(ms), temperature_minimum_delta (Celcius*1000), log max interval
def get_device_info(device_file):
            parts = os.path.split(device_file)     #take off the file
            parts2 = os.path.split(parts[0]) #and get the directory
            device = parts2[1]
            with sqlite3.connect(dbname) as conn:
                curs=conn.cursor()
                cmd = u"Select device, friendly_name, t_check_interval, t_delta_minimum, l_maximum_interval from devices where device = '{0}'".format(device)
                curs.execute(cmd)
                data = curs.fetchone()
                return data

#returns the last temperature for this device
def get_last_temperature(device):
    try:
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            cmd = u"Select timestamp, temperature from temperatures where device='{0}' order by timestamp desc limit 1".format(device)
            curs.execute(cmd)
            data = curs.fetchone()
            if data is None:  #len(data)!=2:
                ts = datetime.datetime.now() - datetime.timedelta(days=1)
                tstr =unicode(ts)
                data=tstr,0
            return data
    except:
                ts = datetime.datetime.now() - datetime.timedelta(days=1)
                tstr =unicode(ts)
                data=tstr,0
                return data

def do_logging(device_file):
        device_info = get_device_info(device_file)
        temperature = get_temp(device_file)
        if temperature == None:
            # Sometimes reads fail on the first attempt
            # so we need to retry
            temperature = get_temp(device_file)
        # Store the temperature in the database
        if temperature!= None:
            last_data = get_last_temperature(device_info[0])
            temperature_delta_large_enough = abs(temperature-float(last_data[1])) > float(device_info[3])/1000
            last_data = get_last_temperature(device_info[0])
            temperature_delta_large_enough = abs(temperature-float(last_data[1])) > float(device_info[3])/1000
            nowstring = unicode(datetime.datetime.now())
            nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
            lastdate=datetime.datetime.strptime(last_data[0],u"%Y-%m-%d %H:%M:%S.%f")
            time_delta = nowdate - lastdate
            secondssincelastlog = time_delta.total_seconds()
            maxtimebetweenlogs = float(device_info[4])/1000
            time_delta_long_enough = secondssincelastlog > maxtimebetweenlogs
 #           print temperature, last_data[1],  temperature_delta_large_enough, nowdate, lastdate, time_delta_long_enough
            if temperature_delta_large_enough or time_delta_long_enough:
                string = u"{0} {4:5.1f} {3: <16}   loggging '{1}', '{2:7.3f}'".format (unicode(datetime.datetime.now())[:19], device_info[0], temperature, device_info[1], (32 + (temperature * 9/5)))
                print (string),
                sys.stdout.flush()
                print u"CTRL-z to quit."
                sys.stdout.flush()
                log_temperature(device_info[0], temperature)
                
            


# main function
# This is where the program starts 
def main():
    devicefiles = []
    # enable kernel modules
    os.system(u'sudo modprobe w1-gpio')
    os.system(u'sudo modprobe w1-therm')
 
    # search for a devices file that start with 28
    devicelist = glob.glob(u'/sys/bus/w1/devices/28*')
    if devicelist==[]:
        devicelist = glob.glob(u'./data/28*')
        if devicelist==[]:
            print u'no devices found'
            return
            
    for device in devicelist:
        devicefiles.append(device + u'/w1_slave')
        
#    while True:


#
#
#    device_info = get_device_info(devicefiles[0]) 
#    temperature = get_temp(devicefiles[0])
#    last_data = get_last_temperature(device_info[0])
#    temperature_delta_large_enough = abs(temperature-float(last_data[1])) > float(device_info[3])/1000
#    nowstring = str(datetime.datetime.now())
#    nowdate = datetime.datetime.strptime(nowstring,"%Y-%m-%d %H:%M:%S.%f")
#    lastdate=datetime.datetime.strptime(last_data[0],"%Y-%m-%d %H:%M:%S.%f")
#    time_delta = nowdate - lastdate
#    time_delta_long_enough = time_delta.total_seconds()> float (device_info[2])/1000
#    
 


    # get the temperature from the device file
    loggers = []
    for device_file in devicefiles:
        device_info = get_device_info(device_file) 
        check_interval = device_info[2]/1000
        last_temperature = get_last_temperature(device_info[0])
        t = perpetualTimer(check_interval,do_logging,device_file)
        loggers.append(t)
    for t in loggers:
        t.start()
    print u"finished starting loggers"
#    sleep(60)
#    print "cancelling"
#    for t in loggers:
#        t.cancel()
#    print "loggers cancelled"
#    char =' '
#    while char!='q' and char!= 'Q':
#        char = getch()
#        print char,
#    t.cancel()
    
if __name__==u"__main__":
    main()




