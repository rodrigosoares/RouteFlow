#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import logging
import threading
import time
import json
import requests
import ipaddress
import rflib.ipc.MongoIPC as MongoIPC
from rflib.ipc.RFProtocol import *
from rflib.defs import *
from rflib.types.Match import *
from rflib.types.Action import *
from rflib.types.Option import *

CT_ID = 0

class RFHavox():
    def __init__(self):
        self.__define_logger()
        self.__define_ipc()
        self.__request_rules()
        self.__install_rules()

    def __define_logger(self):
        self.log = logging.getLogger('rfhavox')
        self.log.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        self.log.addHandler(ch)

    def __define_ipc(self):
        self.ipc = MongoIPC.MongoIPCMessageService(
            MONGO_ADDRESS, MONGO_DB_NAME, RFSERVER_ID,
            threading.Thread, time.sleep)

    def __request_rules(self):
        url = 'http://192.168.56.1:4567/rules'
        dot_file = './hvxfiles/routeflow.dot'
        hvx_file = './hvxfiles/routeflow.hvx'
        self.log.info('Requesting special rules from the Havox API')
        self.log.info("URL: %s" % url)
        self.log.info('Reading files')
        self.log.info("Topology file: %s" % dot_file)
        self.log.info("Instructions file: %s" % hvx_file)
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

    def __install_rules(self):
        self.log.info("%i rules will be installed" % len(self.havox_rules))
        dp_ids = list(set([rule['dp_id'] for rule in self.havox_rules]))
        for dp_id in dp_ids:
            self.__install_rules_in_datapath(CT_ID, dp_id)

    def __add_matches(self, rm, matches):
        for field, value in matches:
            match_str = field.upper()
            if match_str == 'IPV4_SRC':
                match = None # RouteFlow does not implement IPv4 source yet.
            elif match_str == 'IPV4':
                netw = ipaddress.ip_network(value)
                ip = netw.network_address
                netmask = netw.netmask
                match = eval("Match.IPV4('%s', '%s')" % (ip, netmask))
            else:
                match = eval("Match.%s(%d)" % (match_str, value))
            if match is not None: rm.add_match(match)

    def __add_actions(self, rm, actions):
        for action_obj in actions:
            action_str = action_obj['action'].upper()
            action = eval("Action.%s(%d)" % (action_str, action_obj['arg_a']))
            rm.add_action(action)

    def __install_rules_in_datapath(self, ct_id, dp_id):
        dp_rules = filter(lambda rule: rule['dp_id'] == dp_id, self.havox_rules)
        for rule in dp_rules:
            rm = RouteMod(RMT_ADD, dp_id)
            rm.add_option(Option.PRIORITY(PRIORITY_HIGHEST))
            self.__add_matches(rm, rule['matches'].items())
            self.__add_actions(rm, rule['actions'])
            rm.add_option(Option.CT_ID(ct_id))
            self.ipc.send(RFSERVER_RFPROXY_CHANNEL, str(ct_id), rm)


if __name__ == '__main__':
    try:
        RFHavox()
    except IOError:
        sys.exit('Could not open files for upload.')
