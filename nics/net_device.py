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


import os
import re
from functools import wraps
import time


import settings
from crb import Crb
from settings import TIMEOUT

NICS_LIST = []      # global list for save nic objects


class NetDevice(object):

    """
    Abstract the device which is PF or VF.
    """

    def __init__(self, crb, bus_id, devfun_id):
        if not isinstance(crb, Crb):
            raise Exception("  Please input the instance of Crb!!!")
        self.crb = crb
        self.bus_id = bus_id
        self.devfun_id = devfun_id
        self.pci = bus_id + ':' + devfun_id
        self.pci_id = get_pci_id(crb, bus_id, devfun_id)
        self.default_driver = settings.get_nic_driver(self.pci_id)

        if self.nic_is_pf():
            self.default_vf_driver = ''
        self.get_interface_name()
        self.socket = self.get_nic_socket()

    def stop(self):
        pass

    def close(self):
        pass

    def setup(self):
        pass

    def __send_expect(self, cmds, expected, timeout=TIMEOUT, alt_session=True):
        """
        Wrap the crb`s session as private session for sending expect.
        """
        return self.crb.send_expect(cmds, expected, timeout=timeout, alt_session=alt_session)

    def __get_os_type(self):
        """
        Get OS type.
        """
        return self.crb.get_os_type()

    def nic_is_pf(self):
        """
        It is the method that you can check if the nic is PF.
        """
        return True

    def nic_has_driver(func):
        """
        Check if the NIC has a driver.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            nic_instance = args[0]
            nic_instance.current_driver = nic_instance.get_nic_driver()
            if not nic_instance.current_driver:
                return ''
            return func(*args, **kwargs)
        return wrapper

    def get_nic_driver(self):
        """
        Get the NIC driver.
        """
        return self.crb.get_pci_dev_driver(self.bus_id, self.devfun_id)

    def get_nic_socket(self):
        """
        Get socket id of specified pci device.
        """
        get_nic_socket = getattr(
            self, 'get_nic_socket_%s' %
            self.__get_os_type())
        return get_nic_socket(self.bus_id, self.devfun_id)

    def get_nic_socket_linux(self, bus_id, devfun_id):
        command = ('cat /sys/bus/pci/devices/0000\:%s\:%s/numa_node' %
                   (bus_id, devfun_id))
        try:
            out = self.__send_expect(command, '# ')
            socket = int(out)
        except:
            socket = -1
        return socket

    def get_nic_socket_freebsd(self, bus_id, devfun_id):
        NotImplemented

    @nic_has_driver
    def get_interface_name(self):
        """
        Get interface name of specified pci device.
        Cal this function will update intf_name everytime
        """
        get_interface_name = getattr(
            self, 'get_interface_name_%s' %
            self.__get_os_type())
        out = get_interface_name(self.bus_id, self.devfun_id, self.current_driver)
        if "No such file or directory" in out:
            self.intf_name = 'N/A'
        else:
            self.intf_name = out

        return self.intf_name

    def get_interface_name_linux(self, bus_id, devfun_id, driver):
        """
        Get interface name of specified pci device on linux.
        """
        driver_alias = driver.replace('-', '_')
        try:
            get_interface_name_linux = getattr(
                self,
                'get_interface_name_linux_%s' %
                driver_alias)
        except Exception as e:
            generic_driver = 'generic'
            get_interface_name_linux = getattr(self,
                                               'get_interface_name_linux_%s' % generic_driver)

        return get_interface_name_linux(bus_id, devfun_id)

    def get_interface_name_linux_virtio_pci(self, bus_id, devfun_id):
        """
        Get virtio device interface name by the default way on linux.
        """
        command = 'ls --color=never /sys/bus/pci/devices/0000\:%s\:%s/virtio*/net' % (
            bus_id, devfun_id)
        return self.__send_expect(command, '# ')

    def get_interface_name_linux_generic(self, bus_id, devfun_id):
        """
        Get the interface name by the default way on linux.
        """
        command = 'ls --color=never /sys/bus/pci/devices/0000\:%s\:%s/net' % (
            bus_id, devfun_id)
        return self.__send_expect(command, '# ')

    def get_interface_name_freebsd(self, bus_id, devfun_id, driver):
        """
        Get interface name of specified pci device on Freebsd.
        """
        try:
            get_interface_name_freebsd = getattr(self,
                                                 'get_interface_name_freebsd_%s' % driver)
        except Exception as e:
            generic_driver = 'generic'
            get_interface_name_freebsd = getattr(self,
                                                 'get_interface_name_freebsd_%s' % generic_driver)

        return get_interface_name_freebsd(bus_id, devfun_id)

    def get_interface_name_freebsd_generic(self, bus_id, devfun_id):
        """
        Get the interface name by the default way on freebsd.
        """
        out = self.__send_expect("pciconf -l", "# ")
        rexp = r"(\w*)@pci0:%s" % bus_id
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        if len(match) == 0:
            return "No such file"
        return match[0]

    @nic_has_driver
    def set_vf_mac_addr(self, vf_idx=0, mac="00:00:00:00:00:01"):
        """
        Set mac address of specified vf device.
        """
        set_vf_mac_addr = getattr(self, 'set_vf_mac_addr_%s' % self.__get_os_type())
        out = set_vf_mac_addr(self.intf_name, vf_idx, mac)

    def set_vf_mac_addr_linux(self, intf, vf_idx, mac):
        """
        Set mac address of specified vf device on linux.
        """
        if self.current_driver != self.default_driver:
            print "Only support when PF bound to default driver"
            return

        self.__send_expect("ip link set %s vf %d mac %s" % (intf, vf_idx, mac), "# ")

    @nic_has_driver
    def get_mac_addr(self):
        """
        Get mac address of specified pci device.
        """
        get_mac_addr = getattr(self, 'get_mac_addr_%s' % self.__get_os_type())
        out = get_mac_addr(self.intf_name, self.bus_id, self.devfun_id, self.current_driver)
        if "No such file or directory" in out:
            return 'N/A'
        else:
            return out

    def get_mac_addr_linux(self, intf, bus_id, devfun_id, driver):
        """
        Get mac address of specified pci device on linux.
        """
        driver_alias = driver.replace('-', '_')
        try:
            get_mac_addr_linux = getattr(
                self,
                'get_mac_addr_linux_%s' %
                driver_alias)
        except Exception as e:
            generic_driver = 'generic'
            get_mac_addr_linux = getattr(
                self,
                'get_mac_addr_linux_%s' %
                generic_driver)

        return get_mac_addr_linux(intf, bus_id, devfun_id, driver)

    def get_mac_addr_linux_generic(self, intf, bus_id, devfun_id, driver):
        """
        Get MAC by the default way on linux.
        """
        command = ('cat /sys/bus/pci/devices/0000\:%s\:%s/net/%s/address' %
                   (bus_id, devfun_id, intf))
        return self.__send_expect(command, '# ')

    def get_mac_addr_linux_virtio_pci(self, intf, bus_id, devfun_id, driver):
        """
        Get MAC by the default way on linux.
        """
        virtio_cmd = ('ls /sys/bus/pci/devices/0000\:%s\:%s/ | grep --color=never virtio' %
                      (bus_id, devfun_id))
        virtio = self.__send_expect(virtio_cmd, '# ')

        command = ('cat /sys/bus/pci/devices/0000\:%s\:%s/%s/net/%s/address' %
                   (bus_id, devfun_id, virtio, intf))
        return self.__send_expect(command, '# ')

    def get_mac_addr_freebsd(self, intf, bus_id, devfun_id, driver):
        """
        Get mac address of specified pci device on Freebsd.
        """
        try:
            get_mac_addr_freebsd = getattr(
                self,
                'get_mac_addr_freebsd_%s' %
                driver)
        except Exception as e:
            generic_driver = 'generic'
            get_mac_addr_freebsd = getattr(
                self,
                'get_mac_addr_freebsd_%s' %
                generic_driver)

        return get_mac_addr_freebsd(intf, bus_id, devfun_id)

    def get_mac_addr_freebsd_generic(self, intf, bus_id, devfun_id):
        """
        Get the MAC by the default way on Freebsd.
        """
        out = self.__send_expect('ifconfig %s' % intf, '# ')
        rexp = r"ether ([\da-f:]*)"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        return match[0]

    @nic_has_driver
    def get_ipv4_addr(self):
        """
        Get ipv4 address of specified pci device.
        """
        get_ipv4_addr = getattr(
            self, 'get_ipv4_addr_%s' % self.__get_os_type())
        return get_ipv4_addr(self.intf_name, self.currenct_driver)

    def get_ipv4_addr_linux(self, intf, driver):
        """
        Get ipv4 address of specified pci device on linux.
        """
        try:
            get_ipv4_addr_linux = getattr(self, 'get_ipv4_linux_%s' % driver)
        except Exception as e:
            generic_driver = 'generic'
            get_ipv4_addr_linux = getattr(
                self, 'get_ipv4_linux_%s' %
                generic_driver)

        return get_ipv4_addr_linux(intf, bus_id, devfun_id, driver)

    def get_ipv4_addr_linux_generic(self, intf):
        """
        Get IPv4 address by the default way on linux.
        """
        out = self.__send_expect("ip -family inet address show dev %s | awk '/inet/ { print $2 }'"
                                 % intf, "# ")
        return out.split('/')[0]

    def get_ipv4_addr_freebsd(self, intf, driver):
        """
        Get ipv4 address of specified pci device on Freebsd.
        """
        try:
            get_ipv4_addr_freebsd = getattr(
                self,
                'get_ipv4_addr_freebsd_%s' %
                driver)
        except Exception as e:
            generic_driver = 'generic'
            get_ipv4_addr_freebsd = getattr(
                self,
                'get_ipv4_addr_freebsd_%s' %
                generic_driver)

        return get_ipv4_addr_freebsd(intf, bus_id, devfun_id)

    def get_ipv4_addr_freebsd_generic(self, intf):
        """
        Get the IPv4 address by the default way on Freebsd.
        """
        out = self.__send_expect('ifconfig %s' % intf, '# ')
        rexp = r"inet ([\d:]*)%"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        if len(match) == 0:
            return None

        return match[0]

    @nic_has_driver
    def enable_ipv6(self):
        """
        Enable ipv6 address of specified pci device.
        """
        if self.current_driver != self.default_driver:
            return

        enable_ipv6 = getattr(
            self, 'enable_ipv6_%s' % self.__get_os_type())
        return enable_ipv6(self.intf_name)

    def enable_ipv6_linux(self, intf):
        """
        Enable ipv6 address of specified pci device on linux.
        """
        self.__send_expect("sysctl net.ipv6.conf.%s.disable_ipv6=0" %
                           intf, "# ")
        # FVL interface need down and up for re-enable ipv6
        if self.default_driver == 'i40e':
            self.__send_expect("ifconfig %s down" % intf, "# ")
            self.__send_expect("ifconfig %s up" % intf, "# ")

    def enable_ipv6_freebsd(self, intf):
        pass

    @nic_has_driver
    def disable_ipv6(self):
        """
        Disable ipv6 address of specified pci device.
        """
        if self.current_driver != self.default_driver:
            return
        disable_ipv6 = getattr(
            self, 'disable_ipv6_%s' % self.__get_os_type())
        return disable_ipv6(self.intf_name)

    def disable_ipv6_linux(self, intf):
        """
        Disable ipv6 address of specified pci device on linux.
        """
        self.__send_expect("sysctl net.ipv6.conf.%s.disable_ipv6=1" %
                           intf, "# ")

    def disable_ipv6_freebsd(self, intf):
        pass

    @nic_has_driver
    def get_ipv6_addr(self):
        """
        Get ipv6 address of specified pci device.
        """
        get_ipv6_addr = getattr(
            self, 'get_ipv6_addr_%s' % self.__get_os_type())
        return get_ipv6_addr(self.intf_name, self.current_driver)

    @nic_has_driver
    def get_ipv6_addr(self):
        """
        Get ipv6 address of specified pci device.
        """
        get_ipv6_addr = getattr(
            self, 'get_ipv6_addr_%s' % self.__get_os_type())
        return get_ipv6_addr(self.intf_name, self.current_driver)

    def get_ipv6_addr_linux(self, intf, driver):
        """
        Get ipv6 address of specified pci device on linux.
        """
        try:
            get_ipv6_addr_linux = getattr(
                self,
                'get_ipv6_addr_linux_%s' %
                driver)
        except Exception as e:
            generic_driver = 'generic'
            get_ipv6_addr_linux = getattr(
                self,
                'get_ipv6_addr_linux_%s' %
                generic_driver)

        return get_ipv6_addr_linux(intf)

    def get_ipv6_addr_linux_generic(self, intf):
        """
        Get the IPv6 address by the default way on linux.
        """
        out = self.__send_expect("ip -family inet6 address show dev %s | awk '/inet6/ { print $2 }'"
                                 % intf, "# ")
        return out.split('/')[0]

    def get_ipv6_addr_freebsd(self, intf, driver):
        """
        Get ipv6 address of specified pci device on Freebsd.
        """
        try:
            get_ipv6_addr_freebsd = getattr(
                self,
                'get_ipv6_addr_freebsd_%s' %
                driver)
        except Exception as e:
            generic_driver = 'generic'
            get_ipv6_addr_freebsd = getattr(
                self,
                'get_ipv6_addr_freebsd_%s' %
                generic_driver)

        return get_ipv6_addr_freebsd(intf)

    def get_ipv6_addr_freebsd_generic(self, intf):
        """
        Get the IPv6 address by the default way on Freebsd.
        """
        out = self.__send_expect('ifconfig %s' % intf, '# ')
        rexp = r"inet6 ([\da-f:]*)%"
        pattern = re.compile(rexp)
        match = pattern.findall(out)
        if len(match) == 0:
            return None

        return match[0]

    def get_nic_numa(self):
        """
        Get numa number of specified pci device.
        """
        self.crb.get_nic_numa(self.bus_id, self.devfun_id)

    def get_card_type(self):
        """
        Get card type of specified pci device.
        """
        return self.crb.get_pci_dev_id(self.bus_id, self.devfun_id)

    @nic_has_driver
    def get_sriov_vfs_pci(self):
        """
        Get all SRIOV VF pci bus of specified pci device.
        """
        get_sriov_vfs_pci = getattr(
            self, 'get_sriov_vfs_pci_%s' % self.__get_os_type())
        return get_sriov_vfs_pci(self.bus_id, self.devfun_id, self.current_driver)

    def get_sriov_vfs_pci_linux(self, bus_id, devfun_id, driver):
        """
        Get all SRIOV VF pci bus of specified pci device on linux.
        """
        try:
            get_sriov_vfs_pci_linux = getattr(
                self,
                'get_sriov_vfs_pci_linux_%s' %
                driver)
        except Exception as e:
            generic_driver = 'generic'
            get_sriov_vfs_pci_linux = getattr(
                self,
                'get_sriov_vfs_pci_linux_%s' %
                generic_driver)

        return get_sriov_vfs_pci_linux(bus_id, devfun_id)

    def get_sriov_vfs_pci_linux_generic(self, bus_id, devfun_id):
        """
        Get all the VF PCIs of specified PF by the default way on linux.
        """
        sriov_numvfs = self.__send_expect(
            "cat /sys/bus/pci/devices/0000\:%s\:%s/sriov_numvfs" %
            (bus_id, devfun_id), "# ")
        sriov_vfs_pci = []

        if "No such file" in sriov_numvfs:
            return sriov_vfs_pci

        if int(sriov_numvfs) == 0:
            pass
        else:
            try:
                virtfns = self.__send_expect(
                    "ls -d /sys/bus/pci/devices/0000\:%s\:%s/virtfn*" %
                    (bus_id, devfun_id), "# ")
                for virtfn in virtfns.split():
                    vf_uevent = self.__send_expect(
                        "cat %s" %
                        os.path.join(virtfn, "uevent"), "# ")
                    vf_pci = re.search(
                        r"PCI_SLOT_NAME=0000:([0-9a-f]+:[0-9a-f]+\.[0-9a-f]+)",
                        vf_uevent).group(1)
                    sriov_vfs_pci.append(vf_pci)
            except Exception as e:
                print "Scan linux port [0000:%s.%s] sriov vf failed: %s" % (bus_id, devfun_id, e)

        return sriov_vfs_pci

    @nic_has_driver
    def generate_sriov_vfs(self, vf_num):
        """
        Generate some numbers of SRIOV VF.
        """
        if vf_num == 0:
            self.bind_vf_driver()
        generate_sriov_vfs = getattr(
            self, 'generate_sriov_vfs_%s' %
            self.__get_os_type())
        generate_sriov_vfs(
            self.bus_id,
            self.devfun_id,
            vf_num,
            self.current_driver)
        if vf_num != 0:
            self.sriov_vfs_pci = self.get_sriov_vfs_pci()

            vf_pci = self.sriov_vfs_pci[0]
            addr_array = vf_pci.split(':')
            bus_id = addr_array[0]
            devfun_id = addr_array[1]

            self.default_vf_driver = self.crb.get_pci_dev_driver(
                bus_id, devfun_id)
        else:
            self.sriov_vfs_pci = []
        time.sleep(1)

    def generate_sriov_vfs_linux(self, bus_id, devfun_id, vf_num, driver):
        """
        Generate some numbers of SRIOV VF.
        """
        try:
            generate_sriov_vfs_linux = getattr(
                self,
                'generate_sriov_vfs_linux_%s' %
                driver)
        except Exception as e:
            generic_driver = 'generic'
            generate_sriov_vfs_linux = getattr(
                self,
                'generate_sriov_vfs_linux_%s' %
                generic_driver)

        return generate_sriov_vfs_linux(bus_id, devfun_id, vf_num)

    def generate_sriov_vfs_linux_generic(self, bus_id, devfun_id, vf_num):
        """
        Generate SRIOV VFs by the default way on linux.
        """
        nic_driver = self.get_nic_driver()

        if not nic_driver:
            return None

        vf_reg_file = "sriov_numvfs"
        vf_reg_path = os.path.join("/sys/bus/pci/devices/0000:%s:%s" %
                                   (bus_id, devfun_id), vf_reg_file)
        self.__send_expect("echo %d > %s" %
                           (int(vf_num), vf_reg_path), "# ")

    def generate_sriov_vfs_linux_igb_uio(self, bus_id, devfun_id, vf_num):
        """
        Generate SRIOV VFs by the special way of igb_uio driver on linux.
        """
        nic_driver = self.get_nic_driver()

        if not nic_driver:
            return None

        vf_reg_file = "max_vfs"
        if self.default_driver == 'i40e':
            regx_reg_path = "find /sys -name %s | grep %s:%s" % (vf_reg_file, bus_id, devfun_id)
            vf_reg_path = self.__send_expect(regx_reg_path, "# ")
        else:
            vf_reg_path = os.path.join("/sys/bus/pci/devices/0000:%s:%s" %
                                       (bus_id, devfun_id), vf_reg_file)
        self.__send_expect("echo %d > %s" %
                           (int(vf_num), vf_reg_path), "# ")

    def destroy_sriov_vfs(self):
        """
        Destroy the SRIOV VFs.
        """
        self.generate_sriov_vfs(0)

    def bind_vf_driver(self, pci='', driver=''):
        """
        Bind the specified driver to VF.
        """
        bind_vf_driver = getattr(self, 'bind_driver_%s' % self.__get_os_type())
        if not driver:
            if not self.default_vf_driver:
                print "Must specify a driver because default VF driver is NULL!"
                return
            driver = self.default_vf_driver

        if not pci:
            if not self.sriov_vfs_pci:
                print "No VFs on the nic [%s]!" % self.pci
                return
            for vf_pci in self.sriov_vfs_pci:
                addr_array = vf_pci.split(':')
                bus_id = addr_array[0]
                devfun_id = addr_array[1]

                bind_vf_driver(bus_id, devfun_id, driver)
        else:
            addr_array = pci.split(':')
            bus_id = addr_array[0]
            devfun_id = addr_array[1]

            bind_vf_driver(bus_id, devfun_id, driver)

    def bind_driver(self, driver=''):
        """
        Bind specified driver to PF.
        """
        bind_driver = getattr(self, 'bind_driver_%s' % self.__get_os_type())
        if not driver:
            if not self.default_driver:
                print "Must specify a driver because default driver is NULL!"
                return
            driver = self.default_driver
        ret = bind_driver(self.bus_id, self.devfun_id, driver)
        time.sleep(1)
        return ret

    def bind_driver_linux(self, bus_id, devfun_id, driver):
        """
        Bind NIC port to specified driver on linux.
        """
        driver_alias = driver.replace('-', '_')
        try:
            bind_driver_linux = getattr(
                self,
                'bind_driver_linux_%s' %
                driver_alias)
            return bind_driver_linux(bus_id, devfun_id)
        except Exception as e:
            driver_alias = 'generic'
            bind_driver_linux = getattr(
                self,
                'bind_driver_linux_%s' %
                driver_alias)
            return bind_driver_linux(bus_id, devfun_id, driver)

    def bind_driver_linux_generic(self, bus_id, devfun_id, driver):
        """
        Bind NIC port to specified driver by the default way on linux.
        """
        new_id = self.pci_id.replace(':', ' ')
        nic_pci_num = ':'.join(['0000', bus_id, devfun_id])
        self.__send_expect(
            "echo %s > /sys/bus/pci/drivers/%s/new_id" % (new_id, driver), "# ")
        self.__send_expect(
            "echo %s > /sys/bus/pci/devices/0000\:%s\:%s/driver/unbind" %
            (nic_pci_num, bus_id, devfun_id), "# ")
        self.__send_expect(
            "echo %s > /sys/bus/pci/drivers/%s/bind" %
            (nic_pci_num, driver), "# ")
        if driver == self.default_driver:
            itf = self.get_interface_name()
            self.__send_expect("ifconfig %s up" % itf, "# ")

    def bind_driver_linux_pci_stub(self, bus_id, devfun_id):
        """
        Bind NIC port to the pci-stub driver on linux.
        """
        new_id = self.pci_id.replace(':', ' ')
        self.__send_expect(
            "echo %s > /sys/bus/pci/drivers/pci-stub/new_id" % new_id, "# ")
        self.__send_expect(
            "echo %s > /sys/bus/pci/devices/0000\:%s\:%s/driver/unbind" %
            (nic_pci_num, bus_id, devfun_id), "# ")
        self.__send_expect(
            "echo %s > /sys/bus/pci/drivers/pci-stub/bind" %
            nic_pci_num, "# ")

    @nic_has_driver
    def unbind_driver(self, driver=''):
        """
        Unbind driver.
        """
        unbind_driver = getattr(
            self, 'unbind_driver_%s' %
            self.__get_os_type())
        if not driver:
            driver = 'generic'
        ret = unbind_driver(self.bus_id, self.devfun_id, driver)
        time.sleep(1)
        return ret

    def unbind_driver_linux(self, bus_id, devfun_id, driver):
        """
        Unbind driver on linux.
        """
        driver_alias = driver.replace('-', '_')

        unbind_driver_linux = getattr(
            self, 'unbind_driver_linux_%s' % driver_alias)
        return unbind_driver_linux(bus_id, devfun_id)

    def unbind_driver_linux_generic(self, bus_id, devfun_id):
        """
        Unbind driver by the default way on linux.
        """
        nic_pci_num = ':'.join(['0000', bus_id, devfun_id])
        cmd = "echo %s > /sys/bus/pci/devices/0000\:%s\:%s/driver/unbind"
        self.send_expect(cmd % (nic_pci_num, bus_id, devfun_id), "# ")


def get_pci_id(crb, bus_id, devfun_id):
    """
    Return pci device type
    """
    command = ('cat /sys/bus/pci/devices/0000\:%s\:%s/vendor' %
               (bus_id, devfun_id))
    out = crb.send_expect(command, "# ")
    vender = out[2:]
    command = ('cat /sys/bus/pci/devices/0000\:%s\:%s/device' %
               (bus_id, devfun_id))
    out = crb.send_expect(command, '# ')
    device = out[2:]
    return "%s:%s" % (vender, device)


def add_to_list(host, obj):
    """
    Add network device object to global structure
    Parameter 'host' is ip address, 'obj' is netdevice object
    """
    nic = {}
    nic['host'] = host
    nic['pci'] = obj.pci
    nic['port'] = obj
    NICS_LIST.append(nic)


def get_from_list(host, bus_id, devfun_id):
    """
    Get network device object from global structure
    Parameter will by host ip, pci bus id, pci function id
    """
    for nic in NICS_LIST:
        if host == nic['host']:
            pci = ':'.join((bus_id, devfun_id))
            if pci == nic['pci']:
                return nic['port']
    return None


def GetNicObj(crb, bus_id, devfun_id):
    """
    Get network device object. If network device has been initialized, just
    return object. Based on nic type, some special nics like RRC will return
    object different from default.
    """
    # find existed NetDevice object
    obj = get_from_list(crb.crb['My IP'], bus_id, devfun_id)
    if obj:
        return obj

    pci_id = get_pci_id(crb, bus_id, devfun_id)
    nic = settings.get_nic_name(pci_id)

    if nic == 'redrockcanyou':
        # redrockcanyou nic need special initialization
        from fm10k import RedRockCanyou
        obj = RedRockCanyou(crb, bus_id, devfun_id)
    elif nic == 'atwood':
        # atwood nic need special initialization
        from atwood import Atwood
        obj = Atwood(crb, bus_id, devfun_id)
    else:
        obj = NetDevice(crb, bus_id, devfun_id)

    add_to_list(crb.crb['My IP'], obj)
    return obj
