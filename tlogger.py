#!/usr/bin/env python

from __future__ import division
from __future__ import with_statement
import sqlite3

import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
#logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

import threading
import os
import time
import matplotlib
import matplotlib.dates
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange, date2num, num2date
import numpy

from time import sleep
import datetime
import glob
import platform
import sys
from io import open
from collections import namedtuple
if platform.platform().startswith(u'Win'):
    import msvcrt
    logger.info(u'found Windows imported msvcrt')
from pylab import *


# global variables
notOnPi = True
speriod=(15*60)-1
dbname=u'data/tlog.db'
device_info = namedtuple("device_info",[ "device_file", "device_id", "friendly_name", "temp_check_interval", "temp_delta_min", "log_max_interval"] )
exitFlag = False
restartFlag = False
mainlooplock = threading.Lock()


class loggingthread (threading.Thread):
    def __init__(self, device_info):
        threading.Thread.__init__(self,name=device_info.friendly_name)
        self.device_info = device_info

    def run(self):
        logger.info("Starting {0}, id={1}".format(self.device_info.friendly_name, self.device_info.device_id))
        do_log_loop(self.device_info)
        logger.info( "Exiting " + self.device_info.friendly_name)

def do_log_loop(device_info):
    recentlogdates, recentlogtemps = get_recent_logs(device_info.device_id)
    n=0
    while not (exitFlag or restartFlag):
        n=n+1
        if n>99:
            n=0
        logger.debug( "check{1:2.0f} {0: <12} ".format(device_info.friendly_name,n))
        recentlogdates, recentlogtemps = do_logging (device_info, recentlogdates, recentlogtemps)
        logger.debug( "check{1:2.0f} {0: <12} done. \r".format(device_info.friendly_name,n),)
        sys.stdout.flush()

        i=0
        while i<device_info.temp_check_interval/1000 and not (exitFlag or restartFlag):
            i=i+1
            time.sleep(1)

def db_add_device(device):
    try:
        t_check_interval = '15000'  #15 seconds
        t_delta_minimum = '180'  # .1 degree F
        log_maximum_interval = '3600000'  # 1 hour
        device_type = ''
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            cmd = u"INSERT INTO devices values('{0}', '{1}','{2}', '{3}', '{4}', '{5}')".format(device, device[3:],t_check_interval, t_delta_minimum, log_maximum_interval, device_type ) #take off the 28- for the friendly name,
            curs.execute(cmd)
            conn.commit
            return True
    except sqlite3.Error, e:
        logger.critical( u"db_add_device_error %s:" % e.args[0])
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
        logger.critical( u"check_device error %s:" % e.args[0])
        return False
    

# store the temperature in the database
def log_temperature(nowstring, device, temp):

    if not check_device(device):
        logger.critical( u"Could not log {0} {temp} There was problem finding the device in the database.")
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
                logger.info(unicode(value),)
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
        logger.critical (u"Exception opening " + device_file)
        return None

    # get the status from the end of line 1 
    status = lines[0][-4:-1]

    # is the status is ok, get the temperature from line 2
    if status==u"YES":
        tempstr= lines[1].split(u"t=",1)[-1]
        tempvalue=float(tempstr)/1000
        return tempvalue
    else:
        logger.critical( u"There was an error getting the temperature from " + devicefile+u" status="+status)
        return None
    
    #do the actual logging of the temperature    

#returns device, friendly_name, temperature_check_interval(ms), temperature_minimum_delta (Celcius*1000), log max interval
def get_device_info(device_file):
            """

            :rtype : object[]
            """
            parts = os.path.split(device_file)     #take off the file
            parts2 = os.path.split(parts[0]) #and get the directory
            device = parts2[1]
            try:
                with sqlite3.connect(dbname) as conn:
                    curs=conn.cursor()
                    cmd = u"Select device, friendly_name, t_check_interval, t_delta_minimum, l_maximum_interval from devices where device = '{0}'".format(device)
                    curs.execute(cmd)
                    data = curs.fetchone()
                    deviceinfo=device_info(device_file=device_file, device_id=data[0], friendly_name=data[1], temp_check_interval=data[2], temp_delta_min=data[3], log_max_interval=data[4] )
                return deviceinfo
            except:
                logger.warn("device not in database, creating it.")
                db_add_device(device)      #and try again
                with sqlite3.connect(dbname) as conn:
                    curs=conn.cursor()
                    cmd = u"Select device, friendly_name, t_check_interval, t_delta_minimum, l_maximum_interval from devices where device = '{0}'".format(device)
                    curs.execute(cmd)
                    data = curs.fetchone()
                    deviceinfo=device_info(device_file=device_file, device_id=data[0], friendly_name=data[1], temp_check_interval=data[2], temp_delta_min=data[3], log_max_interval=data[4] )
                return deviceinfo





#returns the last temperature for this device
def get_recent_logs(device):
    recentlogdates = []
    recentlogtemps = []
    predictfitpoints = 3 #number of recent log points to use to predict next point.

    try:
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            cmd = u"Select timestamp, temperature from temperatures where device='{0}' order by timestamp desc limit {1:.0f}".format(device,predictfitpoints)
            for row in curs.execute(cmd):
                dt = date2num(datetime.datetime.strptime(row[0], u"%Y-%m-%d %H:%M:%S.%f"))
                recentlogdates.append(dt)
                recentlogtemps.append(float(row[1]))
            if len(recentlogdates)==0:
                recentlogdates.append(matplotlib.dates.date2num(datetime.datetime.now()))
                recentlogtemps.append(0)
            if len(recentlogdates)<predictfitpoints:
                for i in range (len(recentlogdates), predictfitpoints):
                    recentlogdates.append(recentlogdates[i-1]+.000001) #inc date just a hair
                    recentlogtemps.append(recentlogtemps[i-1])
            # if data is None:  #len(data)!=2:
            #     lastdatestring = unicode(datetime.datetime.now())
            #     lastdate = datetime.datetime.strptime(lastdatestring,u"%Y-%m-%d %H:%M:%S.%f")
            #     return lastdate,0
            # lastdate = datetime.datetime.strptime(data[0],u"%Y-%m-%d %H:%M:%S.%f")
            rcds=recentlogdates[::-1]
            rcts=recentlogtemps[::-1]
            return rcds, rcts
    except:
        logger.critical('Exception getting recent logs')
        # nowstring = unicode(datetime.datetime.now())
        # nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
        return None,None

def do_logging(device_info, recentlogdates, recentlogtemps):
    if recentlogdates == None:
        logger.critical("Could not start {0} because there are no recentlogdates".format(device_info.friendly_name))
        return None, None
    temperature = get_temp(device_info.device_file)
    if temperature == None:      # Sometimes reads fail on the first attempt
        temperature = get_temp(device_info.temp_check_interval)# so we need to retry
    # Store the temperature in the database

    if temperature!= None:
        nowstring = unicode(datetime.datetime.now())
        nowdate = date2num(datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f"))

        logger.debug('recentlogdates.len={0:.0f}'.format(len(recentlogdates)))
        timedelta = nowdate - recentlogdates[len(recentlogdates)-1]

        fit = polyfit(recentlogdates,recentlogtemps,1)
        fit_fn = poly1d(fit) # fit_fn is now a function which takes in x and returns an estimate for y
        predictedtemp = fit_fn(nowdate)
        tempdelta = temperature-predictedtemp
        temperature_delta_large_enough = abs(tempdelta) > float(device_info.temp_delta_min/1000)
        maxtimebetweenlogs = float(device_info.log_max_interval/1000)
        timedeltaseconds = timedelta*24*60*60
        time_delta_long_enough = timedeltaseconds > maxtimebetweenlogs
        logger.debug('{0} temp={1:.2f}, predictedtemp={2:.2f}, tempdelta={3:.2f} {4:},timedelta={5:4.0f} {6:}'.format\
                    (device_info.friendly_name, temperature, predictedtemp, tempdelta, temperature_delta_large_enough,
                     timedeltaseconds, time_delta_long_enough))
        logger.debug(device_info.friendly_name+', '+str(recentlogdates)+str(recentlogtemps))
        if temperature_delta_large_enough or time_delta_long_enough:
            log_temperature(nowstring, device_info.device_id, temperature)
            recentlogdates.append(nowdate)
            recentlogdates.pop(0)
            recentlogtemps.append(temperature)
            recentlogtemps.pop(0)
            string = u"{0: <12} {1:5.1f}C {2:7.1f}F".format (device_info.friendly_name, temperature, (32 + (temperature * 9/5)))
            logger.info (string)
            sys.stdout.flush()
    return recentlogdates, recentlogtemps

def get_devicefileslist():
    logger.debug("getting devicefileslist")
    devicefiles = []
    # search for a devices file that start with 28
    devicelist = glob.glob(u'/sys/bus/w1/devices/28*')
    if devicelist==[]:
        devicelist = glob.glob(u'data/28*')
        if devicelist==[]:
            logger.critical( u'no devices found')
            return
    threading._sleep(1)
    for device in devicelist:
        devicefiles.append(device + u'/w1_slave')
    return devicefiles

#returns True if the two lists are the same
def comparedevicefileslists(df1,df2):
    if len(df1)!=len(df2):
        return False
    for i in xrange (len(df1)):
        if df1[i] != df2[i]:
            return False
    return True


# main function
# This is where the program starts 
def main():
    logger.info('starting tlogger')
    # workaround because datetime.datetime.strptime isn't thread safe in windows unless you run it before making the threads
    nowstring = unicode(datetime.datetime.now())
    nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
    global exitFlag
    exitFlag= False
    global restartFlag
    restartFlag = False
    # enable kernel modules
    os.system(u'sudo modprobe w1-gpio')
    os.system(u'sudo modprobe w1-therm')
    loggers = []
    devicefiles = []
    startLoggers = True


    while not exitFlag:
        with mainlooplock:

            logger.debug('mainlooplock started')

            if len(loggers) != len(devicefiles):
                logger.debug('loggers count ({0}) != device files count({}) setting start loggers'.format(len(loggers),len(devicefiles)))
                startLoggers = True         #something changed force a restart

            newdevicefiles = get_devicefileslist()
            if not comparedevicefileslists(newdevicefiles,devicefiles):  #returns true if they are the same
                logger.debug('devicefiles changed, setting start loggers')
                startLoggers = True

            #if they are not the same we will restart everything
            if startLoggers:
                for thread in threading.enumerate():
                    logger.debug(thread.name)

                devicefiles = newdevicefiles
                if len(loggers)>0:
                    restartFlag = True
                    logger.debug("stopping {0} loggers".format(len(loggers)))
                    for thread in threading.enumerate():
                        if thread is not threading.currentThread():
                            logger.debug('waiting for '+thread.name)
                            thread.join()
                    loggers = []
                    restartFlag = False
                    logger.info( "loggers stopped")

                for devicefile in devicefiles:
                    deviceinfo = get_device_info(devicefile)
                    t = loggingthread(deviceinfo)
                    loggers.append(t)
                    logger.debug('added '+deviceinfo.friendly_name)

                for t in loggers:
                    t.start()
                logger.info( u"finished starting {0} loggers".format(len(loggers)))
                startLoggers = False
            logger.debug('checking if {} loggers are alive'.format(len(loggers)))
            for t in loggers:
                if not t.isAlive():
                    logger.debug(t.name + ' is not alive')
                    startLoggers = True
        logger.debug('mainlooplock done')

        # test = raw_input("")
        # if test == 'q' or test=='Q':
        #     exitFlag = True
    logger.info('Exiting the logger')
    for t in loggers:
        t.join()
    logger.info( "Exiting Main Thread")

    
if __name__==u"__main__":
    main()