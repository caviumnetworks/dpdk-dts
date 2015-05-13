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

import time
import dts
import re
import os
from settings import TIMEOUT, IXIA

"""
CRB (customer reference board) basic functions and handlers
"""


class Crb(object):

    """
    Basic module for customer reference board. This module implement functions
    interact with CRB. With these function, we can get the information of
    CPU/PCI/NIC on the board and setup running environment for DPDK.
    """

    def __init__(self, crb, serializer):
        self.crb = crb
        self.read_cache = False
        self.skip_setup = False
        self.serializer = serializer
        self.ports_info = None

    def send_expect(self, cmds, expected, timeout=TIMEOUT,
                    alt_session=False, verify=False):
        """
        Send commands to crb and return string before expected string. If
        there's no expected string found before timeout, TimeoutException will
        be raised.
        """

        if alt_session:
            return self.alt_session.session.send_expect(cmds, expected,
                                                        timeout, verify)

        return self.session.send_expect(cmds, expected, timeout, verify)

    def get_session_output(self, timeout=TIMEOUT):
        """
        Get session output message before timeout
        """
        return self.session.get_session_before(timeout)

    def set_test_types(self, func_tests, perf_tests):
        """
        Enable or disable function/performance test.
        """
        self.want_func_tests = func_tests
        self.want_perf_tests = perf_tests

    def get_total_huge_pages(self):
        """
        Get the huge page number of CRB.
        """
        huge_pages = self.send_expect("awk '/HugePages_Total/ { print $2 }' /proc/meminfo", "# ")
        if huge_pages != "":
            return int(huge_pages)
        return 0

    def mount_huge_pages(self):
        """
        Mount hugepage file system on CRB.
        """
        self.send_expect("umount `awk '/hugetlbfs/ { print $2 }' /proc/mounts`", '# ')
        self.send_expect('mkdir -p /mnt/huge', '# ')
        self.send_expect('mount -t hugetlbfs nodev /mnt/huge', '# ')

    def set_huge_pages(self, huge_pages, numa=-1):
        """
        Set numbers of huge pages
        """
        if numa == -1:
            self.send_expect('echo %d > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages' % huge_pages, '# ', 5)
        else:
            self.send_expect('echo %d > /sys/devices/system/node/node%d/hugepages/hugepages-2048kB/nr_hugepages' % (huge_pages, numa), '# ', 5)

    def set_speedup_options(self, read_cache, skip_setup):
        """
        Configure skip network topology scan or skip DPDK packet setup.
        """
        self.read_cache = read_cache
        self.skip_setup = skip_setup

    def set_directory(self, base_dir):
        """
        Set DPDK package folder name.
        """
        self.base_dir = base_dir

    def admin_ports(self, port, status):
        """
        Force set port's interface status.
        """
        admin_ports_freebsd = getattr(self, 'admin_ports_freebsd_%s' % self.get_os_type())
        return admin_ports_freebsd()

    def admin_ports_freebsd(self, port, status):
        """
        Force set remote interface link status in FreeBSD.
        """
        eth = self.ports_info[port]['intf']
        self.send_expect("ifconfig %s %s" % (eth, status), "# ")

    def admin_ports_linux(self, eth, status):
        """
        Force set remote interface link status in Linux.
        """
        self.send_expect("ip link set  %s %s" % (eth, status), "# ")

    def pci_devices_information(self):
        """
        Scan CRB pci device information and save it into cache file.
        """
        if self.read_cache:
            self.pci_devices_info = self.serializer.load(self.PCI_DEV_CACHE_KEY)

        if not self.read_cache or self.pci_devices_info is None:
            self.pci_devices_information_uncached()
            self.serializer.save(self.PCI_DEV_CACHE_KEY, self.pci_devices_info)

    def pci_devices_information_uncached(self):
        """
        Scan CRB NIC's information on different OS.
        """
        pci_devices_information_uncached = getattr(self, 'pci_devices_information_uncached_%s' % self.get_os_type())
        return pci_devices_information_uncached()

    def pci_devices_information_uncached_linux(self):
        """
        Look for the NIC's information (PCI Id and card type).
        """
        out = self.send_expect("lspci -nn | grep -i eth", "# ")
        rexp = r"([\da-f]{2}:[\da-f]{2}.\d{1}) Ethernet .*?([\da-f]{4}:[\da-f]{4})"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        self.pci_devices_info = []
        for i in range(len(match)):
            self.pci_devices_info.append((match[i][0], match[i][1]))

    def pci_devices_information_uncached_freebsd(self):
        """
        Look for the NIC's information (PCI Id and card type).
        """
        out = self.send_expect("pciconf -l", "# ")
        rexp = r"pci0:([\da-f]{1,3}:[\da-f]{1,2}:\d{1}):\s*class=0x020000.*chip=0x([\da-f]{4})8086"
        pattern = re.compile(rexp)
        match = pattern.findall(out)

        self.pci_devices_info = []
        for i in range(len(match)):
            card_type = "8086:%s" % match[i][1]
            self.pci_devices_info.append((match[i][0], card_type))

    def get_interface_name(self, bus_id, devfun_id=''):
        """
        Get interface name of specified pci device.
        """
        get_interface_name = getattr(self, 'get_interface_name_%s' % self.get_os_type())
        return get_interface_name(bus_id, devfun_id)

    def get_interface_name_linux(self, bus_id, devfun_id):
        """
        Get interface name of specified pci device on linux.
        """
        command = 'ls --color=never /sys/bus/pci/devices/0000:%s:%s/net' % (bus_id, devfun_id)
        out = self.send_expect(command, '# ', verify=True)
        if out == -1:
            name = ""
        else:
            name = out.split()[0]
        return name

    def get_interface_name_freebsd(self, bus_id, devfun_id):
        """
        Get interface name of specified pci device on Freebsd.
        """
        out = self.send_expect("pciconf -l", "# ")
        rexp = r"(\w*)@pci0:%s" % bus_id
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        return match[0]

    def get_mac_addr(self, intf, bus_id='', devfun_id=''):
        """
        Get mac address of specified pci device.
        """
        get_mac_addr = getattr(self, 'get_mac_addr_%s' % self.get_os_type())
        return get_mac_addr(intf, bus_id, devfun_id)

    def get_mac_addr_linux(self, intf, bus_id, devfun_id):
        """
        Get mac address of specified pci device on linux.
        """
        command = ('cat /sys/bus/pci/devices/0000:%s:%s/net/%s/address' %
                   (bus_id, devfun_id, intf))
        return self.send_expect(command, '# ')

    def get_mac_addr_freebsd(self, intf, bus_id, devfun_id):
        """
        Get mac address of specified pci device on Freebsd.
        """
        out = self.send_expect('ifconfig %s' % intf, '# ')
        rexp = r"ether ([\da-f:]*)"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        return match[0]

    def get_device_numa(self, bus_id, devfun_id):
        """
        Get numa id of specified pci device
        """
        numa = self.send_expect("cat /sys/bus/pci/devices/0000\:%s\:%s/numa_node" %
                                (bus_id, devfun_id), "# ")

        try:
            numa = int(numa)
        except ValueError:
            numa = -1
            self.logger.warning("NUMA not available")
        return numa

    def get_ipv6_addr(self, intf):
        """
        Get ipv6 address of specified pci device.
        """
        get_ipv6_addr = getattr(self, 'get_ipv6_addr_%s' % self.get_os_type())
        return get_ipv6_addr(intf)

    def get_ipv6_addr_linux(self, intf):
        """
        Get ipv6 address of specified pci device on linux.
        """
        out = self.send_expect("ip -family inet6 address show dev %s | awk '/inet6/ { print $2 }'"
                               % intf, "# ")
        return out.split('/')[0]

    def get_ipv6_addr_freebsd(self, intf):
        """
        Get ipv6 address of specified pci device on Freebsd.
        """
        out = self.send_expect('ifconfig %s' % intf, '# ')
        rexp = r"inet6 ([\da-f:]*)%"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        if len(match) == 0:
            return None

        return match[0]

    def create_file(self, contents, fileName):
        """
        Create file with contents and copy it to CRB.
        """
        with open(fileName, "w") as f:
            f.write(contents)
        self.session.copy_file_to(fileName)

    def kill_all(self):
        """
        Kill all dpdk applications on CRB.
        """
        cmd = "for i in `lsof /var/run/.rte_config /var/run/dpdk_config \
                | awk '/config/ {print $2}'` ; do kill -9 $i; done"
        self.alt_session.session.send_expect(cmd, "# ", 10)
        time.sleep(.7)

    def close(self):
        """
        Close ssh session of CRB.
        """
        self.session.close()
        self.alt_session.close()

    def get_os_type(self):
        """
        Get OS type from execution configuration file.
        """
        from dut import Dut
        if isinstance(self, Dut) and 'OS' in self.crb:
            return str(self.crb['OS']).lower()

        return 'linux'

    def check_os_type(self):
        """
        Check real OS type whether match configured type.
        """
        from dut import Dut
        expected = 'Linux.*#'
        if isinstance(self, Dut) and self.get_os_type() == 'freebsd':
            expected = 'FreeBSD.*#'

        self.send_expect('uname', expected, 2)

    def init_core_list(self):
        """
        Load or create core information of CRB.
        """
        if self.read_cache:
            self.number_of_cores = self.serializer.load(self.NUMBER_CORES_CACHE_KEY)
            self.cores = self.serializer.load(self.CORE_LIST_CACHE_KEY)

        if not self.read_cache or self.cores is None or self.number_of_cores is None:
            self.init_core_list_uncached()
            self.serializer.save(self.NUMBER_CORES_CACHE_KEY, self.number_of_cores)
            self.serializer.save(self.CORE_LIST_CACHE_KEY, self.cores)

    def init_core_list_uncached(self):
        """
        Scan cores on CRB and create core information list.
        """
        init_core_list_uncached = getattr(self, 'init_core_list_uncached_%s' % self.get_os_type())
        init_core_list_uncached()

    def init_core_list_uncached_freebsd(self):
        """
        Scan cores in Freebsd and create core information list.
        """
        self.cores = []

        import xml.etree.ElementTree as ET

        out = self.send_expect("sysctl -n kern.sched.topology_spec", "# ")

        cpu_xml = ET.fromstring(out)

        # WARNING: HARDCODED VALUES FOR CROWN PASS IVB
        thread = 0
        socket_id = 0

        sockets = cpu_xml.findall(".//group[@level='2']")
        for socket in sockets:
            core_id = 0
            core_elements = socket.findall(".//children/group/cpu")
            for core in core_elements:
                threads = [int(x) for x in core.text.split(",")]
                for thread in threads:
                    if thread != 0:
                        self.cores.append({'socket': socket_id,
                                           'core': core_id,
                                           'thread': thread})
                core_id += 1
            socket_id += 1
        self.number_of_cores = len(self.cores)

    def init_core_list_uncached_linux(self):
        """
        Scan cores in linux and create core information list.
        """
        self.cores = []

        cpuinfo = \
            self.send_expect("grep \"processor\\|physical id\\|core id\\|^$\" /proc/cpuinfo", "#")
        cpuinfo = cpuinfo.split('\r\n\r\n')
        for line in cpuinfo:
            m = re.search("processor\t: (\d+)\r\n" +
                          "physical id\t: (\d+)\r\n" +
                          "core id\t\t: (\d+)", line)

            if m:
                thread = m.group(1)
                socket = m.group(2)
                core = m.group(3)
                if self.crb['bypass core0'] and core == '0' and socket == '0':
                    self.logger.info("Core0 bypassed")
                    continue
                self.cores.append(
                    {'thread': thread, 'socket': socket, 'core': core})

        self.number_of_cores = len(self.cores)

    def get_all_cores(self):
        """
        Return core information list.
        """
        return self.cores

    def remove_hyper_core(self, core_list, key=None):
        """
        Remove hyperthread locre for core list.
        """
        found = set()
        for core in core_list:
            val = core if key is None else key(core)
            if val not in found:
                yield core
                found.add(val)

    def init_reserved_core(self):
        """
        Remove hyperthread cores from reserved list.
        """
        partial_cores = self.cores
        # remove hyper-threading core
        self.reserved_cores = list(self.remove_hyper_core(partial_cores, key=lambda d: (d['core'], d['socket'])))

    def remove_reserved_cores(self, core_list, args):
        """
        Remove cores from reserved cores.
        """
        indexes = sorted(args, reverse=True)
        for index in indexes:
            del core_list[index]
        return core_list

    def get_reserved_core(self, config, socket):
        """
        Get reserved cores by core config and socket id.
        """
        m = re.match("([1-9]+)C", config)
        nr_cores = int(m.group(1))
        if m is None:
            return []

        partial_cores = [n for n in self.reserved_cores if int(n['socket']) == socket]
        if len(partial_cores) < nr_cores:
            return []

        thread_list = [self.reserved_cores[n]['thread'] for n in range(nr_cores)]

        # remove used core from reserved_cores
        rsv_list = [n for n in range(nr_cores)]
        self.reserved_cores = self.remove_reserved_cores(partial_cores, rsv_list)

        # return thread list
        return map(str, thread_list)

    def get_core_list(self, config, th=False, socket=-1):
        """
        Get lcore array according to the core config like "all", "1S/1C/1T".
        We can specify the physical CPU socket by paramter "socket".
        """
        if config == 'all':

            if th:
                return [n['thread'] for n in self.cores]
            else:
                return [n for n in range(0, self.number_of_cores - 1)]

        m = re.match("([1234])S/([1-9]+)C/([12])T", config)

        if m:
            nr_sockets = int(m.group(1))
            nr_cores = int(m.group(2))
            nr_threads = int(m.group(3))

            partial_cores = self.cores

            # If not specify socket sockList will be [0,1] in numa system
            # If specify socket will just use the socket
            if socket < 0:
                sockList = set([int(core['socket']) for core in partial_cores])
            else:
                for n in partial_cores:
                    if (int(n['socket']) == socket):
                        sockList = [int(n['socket'])]

            sockList = list(sockList)[:nr_sockets]
            partial_cores = [n for n in partial_cores if int(n['socket'])
                             in sockList]
            core_list = set([int(n['core']) for n in partial_cores])
            core_list = list(core_list)
            thread_list = set([int(n['thread']) for n in partial_cores])
            thread_list = list(thread_list)

            # filter usable core to core_list
            temp = []
            for sock in sockList:
                core_list = set([int(
                    n['core']) for n in partial_cores if int(n['socket']) == sock])
                core_list = list(core_list)[:nr_cores]
                temp.extend(core_list)

            core_list = temp

            # if system core less than request just use all cores in in socket
            if len(core_list) < (nr_cores * nr_sockets):
                partial_cores = self.cores
                sockList = set([int(n['socket']) for n in partial_cores])

                sockList = list(sockList)[1:nr_sockets + 1]
                partial_cores = [n for n in partial_cores if int(
                    n['socket']) in sockList]
                core_list = set([int(n['core']) for n in partial_cores])
                core_list = list(core_list)
                thread_list = set([int(n['thread']) for n in partial_cores])
                thread_list = list(thread_list)

                temp = []
                for sock in sockList:
                    core_list = set([int(n['core']) for n in partial_cores if int(
                        n['socket']) == sock])
                    core_list = list(core_list)[:nr_cores]
                    temp.extend(core_list)

                core_list = temp

            partial_cores = [n for n in partial_cores if int(
                n['core']) in core_list]
            temp = []
            if len(core_list) < nr_cores:
                return []
            if len(sockList) < nr_sockets:
                return []
            # recheck the core_list and create the thread_list
            i = 0
            for sock in sockList:
                coreList_aux = [int(core_list[n])for n in range(
                    (nr_cores * i), (nr_cores * i + nr_cores))]
                for core in coreList_aux:
                    thread_list = set([int(n['thread']) for n in partial_cores if (
                        (int(n['core']) == core) and (int(n['socket']) == sock))])
                    thread_list = list(thread_list)[:nr_threads]
                    temp.extend(thread_list)
                    thread_list = temp
                i += 1
            return map(str, thread_list)

    def get_lcore_id(self, config):
        """
        Get lcore id of specified core by config "C{socket.core.thread}"
        """

        m = re.match("C{([01]).(\d).([01])}", config)

        if m:
            sockid = m.group(1)
            coreid = int(m.group(2))
            threadid = int(m.group(3))

            perSocklCs = [_ for _ in self.cores if _['socket'] == sockid]
            coreNum = perSocklCs[coreid]['core']

            perCorelCs = [_ for _ in perSocklCs if _['core'] == coreNum]

            return perCorelCs[threadid]['thread']
