# BSD LICENSE
#
# Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Generic port and crbs configuration file load function
"""

import re
import ConfigParser  # config parse module
import argparse      # prase arguments module

portconf = "../conf/ports.cfg"
crbconf = "../conf/crbs.cfg"


class UserConf():

    def __init__(self, port_conf=portconf, crb_conf=crbconf):
        self.port_config = port_conf
        self.crb_config = crb_conf
        self.ports_cfg = {}
        self.pci_regex = "([\da-f]{2}:[\da-f]{2}.\d{1})$"
        try:
            self.port_conf = ConfigParser.SafeConfigParser()
            self.port_conf.read(self.port_config)
        except Exception as e:
            print "FAILED LOADING PORT CONFIG!!!"

    def load_ports_config(self, crbIP):
        ports = []
        for crb in self.port_conf.sections():
            if crb != crbIP:
                continue
            ports = [port.strip()
                     for port in self.port_conf.get(crb, 'ports').split(';')]

        for port in ports:
            port_cfg = self.__parse_port_param(port)
            # check pci BDF validity
            if 'pci' not in port_cfg:
                print "NOT FOUND CONFIG FOR NO PCI ADDRESS!!!"
                continue
            m = re.match(self.pci_regex, port_cfg['pci'])
            if m is None:
                print "INVALID CONFIG FOR NO PCI ADDRESS!!!"
                continue

            keys = port_cfg.keys()
            keys.remove('pci')
            self.ports_cfg[port_cfg['pci']] = {key: port_cfg[key] for key in keys}

    def get_ports_config(self):
        return self.ports_cfg

    def check_port_available(self, pci_addr):
        if pci_addr in self.ports_cfg.keys():
            return True
        else:
            return False

    def __parse_port_param(self, port):
        portDict = dict()

        for param in port.split(','):
            (key, _, value) = param.partition('=')
            if key == 'numa':
                portDict[key] = int(value)
            else:
                portDict[key] = value
        return portDict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Load DTS configuration files")
    parser.add_argument("-p", "--portconf", default=portconf)
    parser.add_argument("-c", "--crbconf", default=crbconf)
    args = parser.parse_args()
    conf = UserConf()
    conf.load_ports_config('192.168.1.1')
    conf.check_port_available('0000:86:00.0')
