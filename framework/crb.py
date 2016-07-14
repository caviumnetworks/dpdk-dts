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
from ssh_connection import SSHConnection
from logger import getLogger

"""
CRB (customer reference board) basic functions and handlers
"""


class Crb(object):

    """
    Basic module for customer reference board. This module implement functions
    interact with CRB. With these function, we can get the information of
    CPU/PCI/NIC on the board and setup running environment for DPDK.
    """

    def __init__(self, crb, serializer, name):
        self.crb = crb
        self.read_cache = False
        self.skip_setup = False
        self.serializer = serializer
        self.ports_info = None
        self.sessions = []
        self.stage = 'pre-init'

        self.logger = getLogger(name)
        self.session = SSHConnection(self.get_ip_address(), name,
                                     self.get_password())
        self.session.init_log(self.logger)
        self.alt_session = SSHConnection(
            self.get_ip_address(),
            name + '_alt',
            self.get_password())
        self.alt_session.init_log(self.logger)

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

    def create_session(self, name=""):
        """
        Create new session for addtional useage. This session will not enable log.
        """
        logger = getLogger(name)
        session = SSHConnection(self.get_ip_address(), name,
                                     self.get_password())
        session.init_log(logger)
        self.sessions.append(session)
        return session

    def destroy_session(self, session=None):
        """
        Destroy addtional session.
        """
        for save_session in self.sessions:
            if save_session == session:
                save_session.close()
                logger = getLogger(save_session.name)
                logger.logger_exit()
            self.sessions.remove(save_session)

    def send_command(self, cmds, timeout=TIMEOUT, alt_session=False):
        """
        Send commands to crb and return string before timeout.
        """

        if alt_session:
            return self.alt_session.session.send_command(cmds, timeout)

        return self.session.send_command(cmds, timeout)

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
        huge_pages = self.send_expect(
            "awk '/HugePages_Total/ { print $2 }' /proc/meminfo",
            "# ", alt_session=True)
        if huge_pages != "":
            return int(huge_pages)
        return 0

    def mount_huge_pages(self):
        """
        Mount hugepage file system on CRB.
        """
        self.send_expect("umount `awk '/hugetlbfs/ { print $2 }' /proc/mounts`", '# ')
        out = self.send_expect("awk '/hugetlbfs/ { print $2 }' /proc/mounts", "# ")
        # only mount hugepage when no hugetlbfs mounted
        if not len(out):
            self.send_expect('mkdir -p /mnt/huge', '# ')
            self.send_expect('mount -t hugetlbfs nodev /mnt/huge', '# ')

    def strip_hugepage_path(self):
        mounts = self.send_expect("cat /proc/mounts |grep hugetlbfs", "# ")
        infos = mounts.split()
        if len(infos) >= 2:
            return infos[1]
        else:
            return ''

    def set_huge_pages(self, huge_pages, numa=-1):
        """
        Set numbers of huge pages
        """
        page_size = self.send_expect("awk '/Hugepagesize/ {print $2}' /proc/meminfo", "# ")

        if numa == -1:
            self.send_expect('echo %d > /sys/kernel/mm/hugepages/hugepages-%skB/nr_hugepages' % (huge_pages, page_size), '# ', 5)
        else:
            #sometimes we set hugepage on kernel cmdline, so we need clear default hugepage
            self.send_expect('echo 0 > /sys/kernel/mm/hugepages/hugepages-%skB/nr_hugepages' % (page_size), '# ', 5)
            
            #some platform not support numa, example vm dut
            try:
                self.send_expect('echo %d > /sys/devices/system/node/node%d/hugepages/hugepages-%skB/nr_hugepages' % (huge_pages, numa, page_size), '# ', 5)
            except:
                self.logger.warning("set %d hugepage on socket %d error" % (huge_pages, numa))
                self.send_expect('echo %d > /sys/kernel/mm/hugepages/hugepages-%skB/nr_hugepages' % (huge_pages. page_size), '# ', 5)

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

    def set_virttype(self, virttype):
        self.virttype = virttype

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
        self.send_expect("ifconfig %s %s" %
                         (eth, status), "# ", alt_session=True)

    def admin_ports_linux(self, eth, status):
        """
        Force set remote interface link status in Linux.
        """
        self.send_expect("ip link set  %s %s" %
                         (eth, status), "# ", alt_session=True)

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
        out = self.send_expect(
            "lspci -Dnn | grep -i eth", "# ", alt_session=True)
        rexp = r"([\da-f]{4}:[\da-f]{2}:[\da-f]{2}.\d{1}) .*Eth.*?ernet .*?([\da-f]{4}:[\da-f]{4})"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        self.pci_devices_info = []
        for i in range(len(match)):
            self.pci_devices_info.append((match[i][0], match[i][1]))

    def pci_devices_information_uncached_freebsd(self):
        """
        Look for the NIC's information (PCI Id and card type).
        """
        out = self.send_expect("pciconf -l", "# ", alt_session=True)
        rexp = r"pci0:([\da-f]{1,3}:[\da-f]{1,2}:\d{1}):\s*class=0x020000.*chip=0x([\da-f]{4})8086"
        pattern = re.compile(rexp)
        match = pattern.findall(out)

        self.pci_devices_info = []
        for i in range(len(match)):
            card_type = "8086:%s" % match[i][1]
            self.pci_devices_info.append((match[i][0], card_type))

    def get_pci_dev_driver(self, domain_id, bus_id, devfun_id):
        """
        Get the driver of specified pci device.
        """
        get_pci_dev_driver = getattr(
            self, 'get_pci_dev_driver_%s' % self.get_os_type())
        return get_pci_dev_driver(domain_id, bus_id, devfun_id)

    def get_pci_dev_driver_linux(self, domain_id, bus_id, devfun_id):
        """
        Get the driver of specified pci device on linux.
        """
        out = self.send_expect("cat /sys/bus/pci/devices/%s\:%s\:%s/uevent" %
                               (domain_id, bus_id, devfun_id), "# ", alt_session=True)
        rexp = r"DRIVER=(.+?)\r"
        pattern = re.compile(rexp)
        match = pattern.search(out)
        if not match:
            return None
        return match.group(1)

    def get_pci_dev_driver_freebsd(self, bus_id, devfun_id):
        """
        Get the driver of specified pci device.
        """
        return True

    def get_pci_dev_id(self, domain_id, bus_id, devfun_id):
        """
        Get the pci id of specified pci device.
        """
        get_pci_dev_id = getattr(
            self, 'get_pci_dev_id_%s' % self.get_os_type())
        return get_pci_dev_id(domain_id, bus_id, devfun_id)

    def get_pci_dev_id_linux(self, domain_id, bus_id, devfun_id):
        """
        Get the pci id of specified pci device on linux.
        """
        out = self.send_expect("cat /sys/bus/pci/devices/%s\:%s\:%s/uevent" %
                               (domain_id, bus_id, devfun_id), "# ", alt_session=True)
        rexp = r"PCI_ID=(.+)"
        pattern = re.compile(rexp)
        match = re.search(out)
        if not match:
            return None
        return match.group(1)

    def get_device_numa(self, domain_id, bus_id, devfun_id):
        """
        Get numa number of specified pci device.
        """
        get_device_numa = getattr(
            self, "get_device_numa_%s" % self.get_os_type())
        return get_device_numa(domain_id, bus_id, devfun_id)

    def get_device_numa_linux(self, domain_id, bus_id, devfun_id):
        """
        Get numa number of specified pci device on Linux.
        """
        numa = self.send_expect(
            "cat /sys/bus/pci/devices/%s\:%s\:%s/numa_node" %
            (domain_id, bus_id, devfun_id), "# ", alt_session=True)

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
                               % intf, "# ", alt_session=True)
        return out.split('/')[0]

    def get_ipv6_addr_freebsd(self, intf):
        """
        Get ipv6 address of specified pci device on Freebsd.
        """
        out = self.send_expect('ifconfig %s' % intf, '# ', alt_session=True)
        rexp = r"inet6 ([\da-f:]*)%"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        if len(match) == 0:
            return None

        return match[0]

    def disable_ipv6(self, intf):
        """
        Disable ipv6 of of specified interface
        """
        if intf != 'N/A':
            self.send_expect("sysctl net.ipv6.conf.%s.disable_ipv6=1" %
                             intf, "# ", alt_session=True)

    def enable_ipv6(self, intf):
        """
        Enable ipv6 of of specified interface
        """
        if intf != 'N/A':
            self.send_expect("sysctl net.ipv6.conf.%s.disable_ipv6=0" %
                             intf, "# ", alt_session=True)

    def create_file(self, contents, fileName):
        """
        Create file with contents and copy it to CRB.
        """
        with open(fileName, "w") as f:
            f.write(contents)
        self.session.copy_file_to(fileName, password=self.get_password())

    def kill_all(self, alt_session=True):
        """
        Kill all dpdk applications on CRB.
        """
        pids = []
        pid_reg = r'p(\d+)'
        cmd = 'lsof -Fp /var/run/.rte_config'
        out = self.send_expect(cmd, "# ", 20, alt_session)
        if len(out):
            lines = out.split('\r\n')
            for line in lines:
                m = re.match(pid_reg, line)
                if m:
                    pids.append(m.group(1))
        for pid in pids:
            self.send_expect('kill -9 %s' % pid, '# ', 20, alt_session)
            self.get_session_output(timeout=2)

        cmd = 'lsof -Fp /var/run/.rte_hugepage_info'
        out = self.send_expect(cmd, "# ", 20, alt_session)
        if len(out) and "No such file or directory" not in out:
            self.logger.warning("There are some dpdk process not free hugepage")
            self.logger.warning("**************************************")
            self.logger.warning(out)
            self.logger.warning("**************************************")

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

        self.send_expect('uname', expected, 2, alt_session=True)

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
            self.send_expect(
                "lscpu -p|grep -v \#",
                "#", alt_session=True)

        cpuinfo = cpuinfo.split()
        # haswell cpu on cottonwood core id not correct
        # need addtional coremap for haswell cpu
        core_id = 0
        coremap = {}
        for line in cpuinfo:
            (thread, core, socket, unused) = line.split(',')[0:4]

            if core not in coremap.keys():
                coremap[core] = core_id
                core_id += 1

            if self.crb['bypass core0'] and core == '0' and socket == '0':
                self.logger.info("Core0 bypassed")
                continue
            self.cores.append(
                    {'thread': thread, 'socket': socket, 'core': coremap[core]})

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

    def get_core_list(self, config, socket=-1):
        """
        Get lcore array according to the core config like "all", "1S/1C/1T".
        We can specify the physical CPU socket by paramter "socket".
        """
        if config == 'all':
            return [n['thread'] for n in self.cores]

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
                    core_list = list([int(n['core']) for n in partial_cores if int(
                        n['socket']) == sock])
                    core_list = core_list[:nr_cores]
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
                    thread_list = list([int(n['thread']) for n in partial_cores if (
                        (int(n['core']) == core) and (int(n['socket']) == sock))])
                    thread_list = thread_list[:nr_threads]
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

    def get_port_info(self, pci):
        """
        return port info by pci id
        """
        for port_info in self.ports_info:
            if port_info['pci'] == pci:
                return port_info
    
    def enable_promisc(self,intf):
        if intf !='N/A':
            self.send_expect("ifconfig %s promisc" %intf, "# ",alt_session=True)
