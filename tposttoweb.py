#!/C:Users\Rick\Anaconda\bin\python
# !/home/rickldftp/anaconda/bin/python
# !/home/rick/anaconda3/envs/py278/bin/python
# __author__ = 'Rick'


import sqlite3
import logging

import requests


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
#logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)
dbname = u'data/tlog.db'
twebposturl = 'http://hallocks.us/cgi-bin/twebpost.py'
twebposturl = 'http://hallocks.us/cgi-bin/hello.py'

def get_local_logs(starttime):
    global dbname
    logs = []
    try:
        with sqlite3.connect(dbname) as conn:
            curs = conn.cursor()
            cmd = u"Select timestamp, device, temperature from temperatures where timestamp > {0} order by timestamp limit 1".format(
                starttime)
            for row in curs.execute(cmd):
                timestamp = row[0]
                device = row[1]
                temperature = row[2]
            return timestamp, device, temperature
    except:
        logger.critical('Exception getting recent logs')
        # nowstring = unicode(datetime.datetime.now())
        # nowdate = datetime.datetime.strptime(nowstring,u"%Y-%m-%d %H:%M:%S.%f")
        return None, None, None


def main():
    logger.info('starting tposttoweb')
    #get the where to start
    payload = {'dbname': 'tlogx'}
    response = requests.get(twebposturl)  #,params=payload
    logger.debug(response)
    # post_data = {'dbname=':'joeb', 'password':'foobar'}
    # post_response = requests.post(url='http://some.other.site', data=post_data)


if __name__ == u"__main__":
    main()