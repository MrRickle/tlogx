#!/usr/bin/python3
__author__ = 'rick'
import ftplib
from ftplib import FTP

import os

spath = u'data'
filepath = u'./data/'
print (os.listdir(filepath))
filename = u'tlog.db'
ftp = ftplib.FTP("ftp.hallocks.us")
ftp.login("tlogx@hallocks.us", "rlhTiiX@7")
ftp.cwd(spath)  #directory to store file in
print ('Before')
ftp.retrlines('LIST')
#os.chdir(r"\\windows\folder\which\has\file")
myfile = open(filepath+filename, 'rb')
ftp.storbinary('STOR '+filename, myfile)
myfile.close()
print ('After')
ftp.retrlines('LIST')

