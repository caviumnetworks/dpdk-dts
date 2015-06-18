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

from exception import ConfigParseException, VirtConfigParseException

PORTCONF = "conf/ports.cfg"
CRBCONF = "conf/crbs.cfg"
VIRTCONF = "conf/virt_global.cfg"


class UserConf():

    def __init__(self, config):
        self.conf = ConfigParser.SafeConfigParser()
        load_files = self.conf.read(config)
        if load_files == []:
            print "FAILED LOADING %s!!!" % config
            self.conf = None
            raise ConfigParseException(config)

    def get_sections(self):
        if self.conf is None:
            return None

        return self.conf.sections()

    def load_section(self, section):
        if self.conf is None:
            return None

        items = None
        for conf_sect in self.conf.sections():
            if conf_sect == section:
                items = self.conf.items(section)

        return items

    def load_config(self, item):
        confs = [conf.strip() for conf in item.split(';')]
        if '' in confs:
            confs.remove('')
        return confs

    def load_param(self, conf):
        paramDict = dict()

        for param in conf.split(','):
            (key, _, value) = param.partition('=')
            paramDict[key] = value
        return paramDict


class VirtConf(UserConf):

    def __init__(self, virt_conf=VIRTCONF):
        self.config_file = virt_conf
        self.virt_cfg = {}
        try:
            self.virt_conf = UserConf(self.config_file)
        except ConfigParseException:
            self.virt_conf = None
            raise VirtConfigParseException

    def load_virt_config(self, name):
        self.virt_cfgs = []

        try:
            virt_confs = self.virt_conf.load_section(name)
        except:
            print "FAILED FIND SECTION %s!!!" % name
            return

        for virt_conf in virt_confs:
            virt_cfg = {}
            virt_params = []
            key, config = virt_conf
            confs = self.virt_conf.load_config(config)
            for config in confs:
                virt_params.append(self.load_virt_param(config))
            virt_cfg[key] = virt_params
            self.virt_cfgs.append(virt_cfg)

    def get_virt_config(self):
        return self.virt_cfgs

    def load_virt_param(self, config):
        cfg_params = self.virt_conf.load_param(config)
        return cfg_params


class PortConf(UserConf):

    def __init__(self, port_conf=PORTCONF):
        self.config_file = port_conf
        self.ports_cfg = {}
        self.pci_regex = "([\da-f]{2}:[\da-f]{2}.\d{1})$"
        try:
            self.port_conf = UserConf(self.config_file)
        except ConfigParseException:
            self.port_conf = None
            raise PortConfigParseException

    def load_ports_config(self, crbIP):
        self.ports_cfg = {}
        if self.port_conf is None:
            return

        ports = self.port_conf.load_section(crbIP)
        if ports is None:
            return
        key, config = ports[0]
        confs = self.port_conf.load_config(config)

        for config in confs:
            port_param = self.port_conf.load_param(config)

            # check pci BDF validity
            if 'pci' not in port_param:
                print "NOT FOUND CONFIG FOR NO PCI ADDRESS!!!"
                continue
            m = re.match(self.pci_regex, port_param['pci'])
            if m is None:
                print "INVALID CONFIG FOR NO PCI ADDRESS!!!"
                continue

            keys = port_param.keys()
            keys.remove('pci')
            self.ports_cfg[port_param['pci']] = {
                key: port_param[key] for key in keys}
            if 'numa' in self.ports_cfg[port_param['pci']]:
                numa_str = self.ports_cfg[port_param['pci']]['numa']
                self.ports_cfg[port_param['pci']]['numa'] = int(numa_str)

    def get_ports_config(self):
        return self.ports_cfg

    def check_port_available(self, pci_addr):
        if pci_addr in self.ports_cfg.keys():
            return True
        else:
            return False



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Load DTS configuration files")
    parser.add_argument("-p", "--portconf", default=PORTCONF)
    parser.add_argument("-c", "--crbconf", default=CRBCONF)
    parser.add_argument("-v", "--virtconf", default=VIRTCONF)
    args = parser.parse_args()

    # not existed configuration file
    try:
        VirtConf('/tmp/not-existed.cfg')
    except VirtConfigParseException:
        print "Capture config parse failure"

    # example for basic use configuration file
    conf = UserConf(PORTCONF)
    for section in conf.get_sections():
        items = conf.load_section(section)
        key, value = items[0]
        confs = conf.load_config(value)
        for config in confs:
            conf.load_param(config)

    # example for port configuration file
    portconf = PortConf(PORTCONF)
    portconf.load_ports_config('DUT IP')
    print portconf.get_ports_config()
    portconf.check_port_available('86:00.0')

    # example for global virtualization configuration file
    virtconf = VirtConf(VIRTCONF)
    virtconf.load_virt_config('LIBVIRT')
    print virtconf.get_virt_config()
