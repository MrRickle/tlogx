#!/usr/bin/env python

import sqlite3

import os
import time
import datetime
import glob

# global variables
notOnPi = True
speriod=(15*60)-1
if notOnPi:
    dbname='./DummyStuff/tlog.db'
else:
    dbname='/var/www/tlog.db'

def db_add_device(device):
    try:
        with sqlite3.connect(dbname) as conn:
            curs=conn.cursor()
            cmd = "INSERT INTO devices values(('"+device+"'), ('"+device+"'))"
            curs.execute(cmd)
            conn.commit
            return True
    except sqlite3.Error, e:
        print "db_add_device_error %s:" % e.args[0]
        return False

def check_device(device):
    try:
        with sqlite3.connect(dbname) as conn:
            curs = conn.cursor()
            cmd = "Select device from devices where device = '"+device+"'"
            curs.execute(cmd)
            data = curs.fetchone()
            conn.commit()
            if data!= None:
                return True
            else:
                return db_add_device(device)
    except sqlite3.Error, e:
        print "check_device error %s:" % e.args[0]
        return False
    

# store the temperature in the database
def log_temperature(device, temp):

    if not check_device(device):
        print "There was problem finding the device in the database."
        return False
        
    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        cmd = "INSERT INTO temperatures values('{0}', '{1}', '{2:2.3}')".format (datetime.datetime.now(), device, temp)
        curs.execute(cmd)
        conn.commit()
        return True
    return False

# display the contents of the database for specified device
def display_data(device):

    with sqlite3.connect(dbname) as conn:
        curs=conn.cursor()
        cmd = "Select * from temperatures where device = '"+device+"'"
        for row in curs.execute(cmd):
            for value in row:
                print str(value),
            print ('')    
        conn.commit()    



# get temerature
# returns None on error, or the temperature as a float
def get_temp(devicefile):

    try:
        fileobj = open(devicefile,'r')
        lines = fileobj.readlines()
        fileobj.close()
    except:
        print ("Exception opening "+devicefile)
        return None

    # get the status from the end of line 1 
    status = lines[0][-4:-1]

    # is the status is ok, get the temperature from line 2
    if status=="YES":
        tempstr= lines[1][-6:-1]
        tempvalue=float(tempstr)/1000
        return tempvalue
    else:
        print "There was an error getting the temperature from " + devicefile+" status="+status
        return None



# main function
# This is where the program starts 
def main():
    devicefiles =[]
    # enable kernel modules
    os.system('sudo modprobe w1-gpio')
    os.system('sudo modprobe w1-therm')

    # search for a device file that starts with 28
    if notOnPi:
        #fake it
        devicelist = glob.glob('./DummyStuff/28*')
    else:
        devicelist = glob.glob('/sys/bus/w1/devices/28*')
    if devicelist=='':
        return None
    else:
        # append /w1slave to the device file
        for device in devicelist:
            devicefiles.append(device + '/w1_slave')


#    while True:

    # get the temperature from the device file
    for file in devicefiles:
        temperature = get_temp(file)
        if temperature == None:
            # Sometimes reads fail on the first attempt
            # so we need to retry
            temperature = get_temp(file)
        # Store the temperature in the database
        if temperature!= None:
            parts = os.path.split(file)     #take off the file
            parts2 = os.path.split(parts[0]) #and get the directory
            device = parts2[1]
            print "{0}', '{1}', '{2:2.3}')".format (datetime.datetime.now(), device, temperature)
            log_temperature(device, temperature)
                # display the contents of the database for this device

    print "finished logging"


if __name__=="__main__":
    main()




