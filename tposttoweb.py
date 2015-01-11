#!/C:Users\Rick\Anaconda\bin\python
# !/home/rickldftp/anaconda/bin/python
# !/home/rick/anaconda3/envs/py278/bin/python
# __author__ = 'Rick'


import sqlite3
import logging

import urllib
import urllib.request
import urllib.error
from urllib.error import URLError, HTTPError
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
#logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)
dbname = 'tlog.db'
dbpath = 'data/' + dbname
twebposturl = 'http://hallocks.us/cgi-bin/twebpost.py'
# twebposturl = 'http://hallocks.us/cgi-bin/hello.py'

def get_local_logs(starttime):
    global dbname
    logs = []
    try:
        with sqlite3.connect(dbpath) as conn:
            curs = conn.cursor()
            cmd = "Select timestamp, device, temperature from temperatures where timestamp > '{0}' order by timestamp limit 1".format(
                starttime)
            for row in curs.execute(cmd):
                timestamp = row[0]
                device = row[1]
                temperature = row[2]
            return timestamp, device, temperature
    except:
        logger.critical('No recent logs (exception getting log)')
        # nowstring = unicode(datetime.datetime.now())
        # nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
        return None, None, None


def main():
    logger.info('starting tposttoweb')
    # get the time to start
    paramstr = '?{0}'.format(dbname)
    urlstr = twebposturl + paramstr
    urlstr = urlstr.replace(' ', '%20')
    with urllib.request.urlopen(urlstr) as f:
        response = str(f.read())
    if response != None:
        match = re.search(r'timestamp="([^"]*)', response)
        lastlogtime = match.group(1)
        logger.debug('{0} lastlogtime={1}'.format(dbname, lastlogtime))
        timestamp, deviceid, temperature = get_local_logs(lastlogtime)
        if deviceid == None:
            logger.info('Quiting, no data found after {0}, must be done!'.format(lastlogtime))
            return
        while timestamp != None and deviceid != None and temperature != None:
            paramstr2 = '?dbname={0}&timestamp={1}&temperature={3}&deviceid={2}'.format(dbname, timestamp, deviceid,
                                                                                        temperature)
            urlstr2 = twebposturl + paramstr2
            urlstr2 = urlstr2.replace(' ', '%20')
            logger.debug('httpcmd ="{0}"'.format(urlstr2))
            try:
                with urllib.request.urlopen(urlstr2) as f2:
                    response2 = str(f2.read())
            except URLError as e:
                logger.critical(e.reason)
                return
            match = re.search(r'timestamp="([^"]*)', response2)
            lastlogtime = match.group(1)
            logger.info('{0} lastlogtime={1}'.format(dbname, lastlogtime))
            timestamp, deviceid, temperature = get_local_logs(lastlogtime)
            logger.debug('{0} nextlogtime={1}'.format(dbname, timestamp))

        #couldn't get requests to work on godaddy, it just returns 406 not acceptable...
        #payload = {'dbname': 'tlogx'}
        #response = requests.get(twebposturl)  #,params=payload
        logger.debug(response)
    # post_data = {'dbname=':'joeb', 'password':'foobar'}
    # post_response = requests.post(url='http://some.other.site', data=post_data)


if __name__ == "__main__":
    main()