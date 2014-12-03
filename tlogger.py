#!/usr/bin/env python

from __future__ import division
from __future__ import with_statement
import sqlite3

import threading

import os
import time

from time import sleep
import datetime
import glob
import platform
import sys
from io import open
from collections import namedtuple
if platform.platform().startswith(u'Win'):
    import msvcrt
    print u'Windows'


# global variables
notOnPi = True
speriod=(15*60)-1
dbname=u'data/tlog.db'
device_info = namedtuple("device_info",[ "device_file", "device_id", "friendly_name", "temp_check_interval", "temp_delta_min", "log_max_interval"] )
exitFlag = False

# class perpetualTimer():
#
#    def __init__(self,t,hFunction,param):
#         print 'ptimer init{0}'.format(param.friendly_name)
#         self.t=t
#         self.hFunction = hFunction
#         self.param = param
#         self.thread = Timer(self.t,self.handle_function)
#
#    def handle_function(self):
#         print 'ptimer handle_function {0}'.format(self.param.friendly_name)
#         self.hFunction(self.param)
#         self.thread = Timer(self.t,self.handle_function)
#         self.thread.start()
#
#    def start(self):
#         print'ptimer start {0}'.format(self.param.friendly_name)
#         self.thread.start()
#
#    def cancel(self):
#         self.thread.cancel()



class loggingthread (threading.Thread):
    def __init__(self, device_info):
        threading.Thread.__init__(self)
        self.device_info = device_info

    def run(self):
        print "Starting {0}, id={1}".format(self.device_info.friendly_name, self.device_info.device_id)
        do_log_loop(self.device_info)
        print "Exiting " + self.device_info.friendly_name

def do_log_loop(device_info):
    lastlogdate, lastlogtemp = get_last_temperature(device_info.device_id)
    lastslope = 0
    n=0
    while not exitFlag:
        n=n+1
        if n>99:
            n=0
        print "\n'Q' to quit,  check{1:2.0f} {0: <12} ".format(device_info.friendly_name,n),
        sys.stdout.flush()
        lastlogdate, lastlogtemp, lastlogslope = do_logging (device_info, lastlogdate, lastlogtemp, lastslope)
        print "check{1:2.0f} {0: <12} done. ".format(device_info.friendly_name,n),
        sys.stdout.flush()

        i=0
        while i<device_info.temp_check_interval/1000 and not exitFlag:
            i=i+1
            time.sleep(1)

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
def log_temperature(nowstring, device, temp):

    if not check_device(device):
        print u"There was problem finding the device in the database."
        return False
        
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        cmd = u"INSERT INTO temperatures values('{0}', '{1}', '{2:2.3}')".format (nowstring, device, temp)
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
        print (u"Exception opening " + device_file)
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
                deviceinfo=device_info(device_file=device_file, device_id=data[0], friendly_name=data[1], temp_check_interval=data[2], temp_delta_min=data[3], log_max_interval=data[4] )
            return deviceinfo


#returns the last temperature for this device
def get_last_temperature(device):
    try:
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            cmd = u"Select timestamp, temperature from temperatures where device='{0}' order by timestamp desc limit 1".format(device)
            curs.execute(cmd)
            data = curs.fetchone()
            if data is None:  #len(data)!=2:
                lastdatestring = unicode(datetime.datetime.now())
                lastdate = datetime.datetime.strptime(lastdatestring,u"%Y-%m-%d %H:%M:%S.%f")
                return lastdate,0
            lastdate = datetime.datetime.strptime(data[0],u"%Y-%m-%d %H:%M:%S.%f")
            return lastdate,data[1]
    except:
        nowstring = unicode(datetime.datetime.now())
        nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
        return nowdate,0

def do_logging(device_info, lastlogdate, lastlogtemp, lastlogslope ):
    temperature = get_temp(device_info.device_file)
    if temperature == None:      # Sometimes reads fail on the first attempt
        temperature = get_temp(device_info.temp_check_interval)# so we need to retry
    # Store the temperature in the database
    if temperature!= None:
        nowstring = unicode(datetime.datetime.now())
        nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
        lastdate = lastlogdate
        time_delta = nowdate - lastdate
        timedeltaseconds = time_delta.total_seconds()
        newslope = (temperature - lastlogtemp)/timedeltaseconds
        predictedtemp = lastlogtemp + (timedeltaseconds * lastlogslope)
        tempdelta = temperature-predictedtemp

        temperature_delta_large_enough = abs(tempdelta) > float(device_info.temp_delta_min/1000)
        maxtimebetweenlogs = float(device_info.log_max_interval/1000)
        time_delta_long_enough = timedeltaseconds > maxtimebetweenlogs
#           print temperature, last_data[1],  temperature_delta_large_enough, nowdate, lastdate, time_delta_long_enough
        if temperature_delta_large_enough or time_delta_long_enough:
            log_temperature(nowstring, device_info.device_id, temperature)
            lastlogslope = (newslope + lastlogslope)/2  #save  the slope for next time, but don't overshoot, makes it zigzag
            lastlogdate = nowdate
            lastlogtemp = temperature
            string = u"{0}  {1: <12} {2:5.1f}C {3:7.3f}F".format (nowstring[:19], device_info.friendly_name, temperature, (32 + (temperature * 9/5)))
            print (string),
            sys.stdout.flush()
    return lastlogdate, lastlogtemp, lastlogslope
            


# main function
# This is where the program starts 
def main():
    # workaround because datetime.datetime.strptime isn't thread safe in windows unless you run it before making the threads
    nowstring = unicode(datetime.datetime.now())
    nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
    print "starting logger at {0}".format(nowdate) #just because we have it here
    global exitFlag
    deviceInfos = []
    #info needed to do the next logging check
    devicefiles = []
    # enable kernel modules
    os.system(u'sudo modprobe w1-gpio')
    os.system(u'sudo modprobe w1-therm')
 
    # search for a devices file that start with 28
    devicelist = glob.glob(u'/sys/bus/w1/devices/28*')
    if devicelist==[]:
        devicelist = glob.glob(u'data/28*')
        if devicelist==[]:
            print u'no devices found'
            return
            
    for device in devicelist:
        devicefiles.append(device + u'/w1_slave')
        
    # get the temperature from the device file
    loggers = []
    for device_file in devicefiles:
        deviceinfo = get_device_info(device_file)
        t = loggingthread(deviceinfo)
        loggers.append(t)
    for t in loggers:
        t.start()
    threading._sleep(1)
    print u"\nfinished starting {0} loggers".format(len(loggers))
    while not exitFlag:
         test = raw_input("")
         if test == 'q' or test=='Q':
            exitFlag = True
            print 'Exiting the logger'
    for t in loggers:
        t.join()
    print "Exiting Main Thread"

    
if __name__==u"__main__":
    main()
