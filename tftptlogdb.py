#!/usr/bin/python3
__author__ = 'rick'
import ftplib
from ftplib import FTP
import logging
import datetime
import os

def getSize(fileobject):
    fileobject.seek(0,2) # move the cursor to the end of the file
    size = fileobject.tell()
    fileobject.seek(0) # move back to the beginning
    return size


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)
logger.debug('starting program')

spath = u'./'
filepath = u'./data/'
filename = u'tlog.db'
ftpsite = "ftp.hallocks.us"
user = "tlogxdata@hallocks.us"
password = "rlhTiiX@7"
nowstring = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
parts = filename.split('.')
destfilename = parts[0]+nowstring+'.'+parts[1]
logger.debug('starting ftp from {0} to {1}'.format(filepath+filename, user+'@'+ftpsite+' '+spath))
ftp = ftplib.FTP(ftpsite)
logger.debug('logging in')
ftp.login(user, password)
logger.debug ('logged in')
ftp.cwd(spath)  #directory to store file in
logger.debug ('directory changed to '+spath)
starttime = datetime.datetime.strptime(str(datetime.datetime.now()),u"%Y-%m-%d %H:%M:%S.%f")
myfile = open(filepath+filename, 'rb')
filesize = getSize(myfile)
ftp.storbinary('STOR '+destfilename, myfile)
myfile.close()
endtime = datetime.datetime.strptime(str(datetime.datetime.now()),u"%Y-%m-%d %H:%M:%S.%f")
copytime = endtime - starttime
seconds = copytime.total_seconds()
logger.debug('It took {0} sec to copy {1} bytes from {2} to {3}'.format(seconds, filesize, filepath+filename, user+'@'+ftpsite+' '+spath+'/'+destfilename))


