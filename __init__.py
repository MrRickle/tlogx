__author__ = 'rick'
#!/usr/bin/python
import ftplib
import os
filename = "tlog.dby"
ftp = ftplib.FTP("xx.xx.xx.xx")
ftp.login("UID", "PSW")
ftp.cwd("/Unix/Folder/where/I/want/to/put/file")
os.chdir(r"\\windows\folder\which\has\file")
myfile = open(filename, 'r')
ftp.storlines('STOR ' + filename, myfile)
myfile.close()
