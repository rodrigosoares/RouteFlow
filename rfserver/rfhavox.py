#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import logging
import threading
import time
import json
import requests
import rflib.ipc.MongoIPC as MongoIPC
from rflib.defs import *

class RFHavox():
    def define_logger(self):
        self.log = logging.getLogger('rfhavox')
        self.log.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        self.log.addHandler(ch)

    def define_ipc(self):
        self.ipc = MongoIPC.MongoIPCMessageService(MONGO_ADDRESS,
                                                   MONGO_DB_NAME,
                                                   RFSERVER_ID,
                                                   threading.Thread,
                                                   time.sleep)

    def request_rules(self):
        url = 'http://192.168.56.1:4567/rules'
        dot_file = './hvxfiles/routeflow.dot'
        hvx_file = './hvxfiles/routeflow.hvx'
        self.log.info('Requesting special rules from the Havox API')
        self.log.info("URL: %s" % url)
        self.log.info("Topology file: %s" % dot_file)
        self.log.info("Instructions file: %s" % hvx_file)
        self.log.info('Reading files')
        files = {'dot_file': open(dot_file, 'r'),
                 'hvx_file': open(hvx_file, 'r')}
        self.log.info('Requesting rules')
        api_data = requests.post(url, files=files,
            data={'qos': 'min(100 Mbps)',
                  'force': 'true',
                  'expand': 'true',
                  'output': 'true',
                  'syntax': 'routeflow'}
        )
        self.log.info('Parsing rules from JSON response')
        self.havox_rules = json.loads(api_data.text)
        self.log.info("Got %i special rules" % len(self.havox_rules))

    def install_rules(self):
        self.log.info("%i rules will be installed" % len(self.havox_rules))

    def __init__(self):
        self.define_logger()
        self.define_ipc()
        self.request_rules()
        self.install_rules()


if __name__ == '__main__':
    try:
        RFHavox()
    except IOError:
        sys.exit('Could not open files for upload.')
