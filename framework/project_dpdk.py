# <COPYRIGHT_TAG>

import os
import re
import dcts

from settings import NICS
from ssh_connection import SSHConnection
from crb import Crb
from dut import Dut
from tester import Tester
from logger import getLogger
from settings import IXIA


class DPDKdut(Dut):

    """
    DPDK project class for DUT. DCTS will call set_target function to setup
    build, memory and kernel module.
    """

    def __init__(self, crb, serializer):
        self.NAME = 'dut'
        super(DPDKdut, self).__init__(crb, serializer)

    def set_target(self, target):
        self.set_toolchain(target)

        # set env variable
        # These have to be setup all the time. Some tests need to compile
        # example apps by themselves and will fail otherwise.
        self.send_expect("export RTE_TARGET=" + target, "#")
        self.send_expect("export RTE_SDK=`pwd`", "#")

        if not self.skip_setup:
            self.build_install_dpdk(target)

        self.setup_memory()
        self.setup_modules(target)

        if self.get_os_type() == 'linux':
            self.bind_interfaces_linux()

    def setup_modules(self, target):
        setup_modules = getattr(self, 'setup_modules_%s' % self.get_os_type())
        setup_modules(target)

    def setup_modules_linux(self, target):
        self.send_expect("modprobe uio", "#", 70)
        self.send_expect("rmmod -f igb_uio", "#", 70)
        self.send_expect("insmod ./" + target + "/kmod/igb_uio.ko", "#", 60)
        out = self.send_expect("lsmod | grep igb_uio", "#")
        assert ("igb_uio" in out), "Failed to insmod igb_uio"

    def setup_modules_freebsd(self, target):
        binding_list = ''

        for (pci_bus, pci_id) in self.pci_devices_info:
            if dcts.accepted_nic(pci_id):
                binding_list += '%s,' % (pci_bus)

        self.send_expect("kldunload if_ixgbe.ko", "#")
        self.send_expect('kenv hw.nic_uio.bdfs="%s"' % binding_list[:-1], '# ')
        self.send_expect("kldload ./%s/kmod/nic_uio.ko" % target, "#", 20)
        out = self.send_expect("kldstat", "#")
        assert ("nic_uio" in out), "Failed to insmod nic_uio"

    def build_install_dpdk(self, target, extra_options=''):
        build_install_dpdk = getattr(self, 'build_install_dpdk_%s' % self.get_os_type())
        build_install_dpdk(target, extra_options)

    def build_install_dpdk_linux(self, target, extra_options):
        # clean all
        self.send_expect("rm -rf " + target, "#")

        # compile
        out = self.send_expect("make -j install T=%s %s" % (target, extra_options), "# ", 120)

        if("Error" in out or "No rule to make" in out):
            self.logger.error("ERROR - try without '-j'")
            # if Error try to execute make without -j option
            out = self.send_expect("make install T=%s %s" % (target, extra_options), "# ", 120)

        assert ("Error" not in out), "Compilation error..."
        assert ("No rule to make" not in out), "No rule to make error..."

    def build_install_dpdk_freebsd(self, target, extra_options):
        # clean all
        self.send_expect("rm -rf " + target, "#")

        # compile
        out = self.send_expect("make -j %d install T=%s CC=gcc48" % (self.number_of_cores,
                                                                     target),
                               "#", 120)

        if("Error" in out or "No rule to make" in out):
            self.logger.error("ERROR - try without '-j'")
            # if Error try to execute make without -j option
            out = self.send_expect("make install T=%s CC=gcc48" % target,
                                   "#", 120)

        assert ("Error" not in out), "Compilation error..."
        assert ("No rule to make" not in out), "No rule to make error..."

    def prerequisites(self, pkgName, patch):
        if not self.skip_setup:
            assert (os.path.isfile(pkgName) is True), "Invalid package"

            self.session.copy_file_to(pkgName)
            if (patch is not None):
                for p in patch:
                    self.session.copy_file_to('../' + p)

            self.kill_all()

            # enable core dump
            self.send_expect("ulimit -c unlimited", "#")
            # copy the core files outside DPDK folder
            self.send_expect("mkdir CORE_DUMP", "#")
            self.send_expect("find %s/ -name core.* -exec cp {} CORE_DUMP \;" %
                             self.base_dir, "#")

            # unpack the code and change to the working folder
            self.send_expect("rm -rf %s" % self.base_dir, "#")

            # unpack dpdk
            out = self.send_expect("tar zxf " + pkgName.split('/')[-1], "# ", 20)
            assert "Error" not in out

            if (patch is not None):
                for p in patch:
                    out = self.send_expect("patch -d %s -p1 < ../%s" %
                                           (self.base_dir, p), "# ")
                    assert "****" not in out

        self.dut_prerequisites()

    def bind_interfaces_linux(self, driver='igb_uio', nics_to_bind=None):
        """
        Bind the interfaces to the selected driver. nics_to_bind can be None
        to bind all interfaces or an array with the port indexes
        """

        binding_list = '--bind=%s ' % driver

        current_nic = 0
        for (pci_bus, pci_id) in self.pci_devices_info:
            if dcts.accepted_nic(pci_id):

                if nics_to_bind is None or current_nic in nics_to_bind:
                    binding_list += '%s ' % (pci_bus)

                current_nic += 1

        self.send_expect('tools/dpdk_nic_bind.py %s' % binding_list, '# ')

    def unbind_interfaces_linux(self, nics_to_bind=None):
        """
        Unbind the interfaces
        """

        binding_list = '-u '

        current_nic = 0
        for (pci_bus, pci_id) in self.pci_devices_info:
            if dcts.accepted_nic(pci_id):

                if nics_to_bind is None or current_nic in nics_to_bind:
                    binding_list += '%s ' % (pci_bus)

                current_nic += 1

        self.send_expect('tools/dpdk_nic_bind.py %s' % binding_list, '# ', 30)

    def build_dpdk_apps(self, folder, extra_options=''):
        build_dpdk_apps = getattr(self, 'build_dpdk_apps_%s' % self.get_os_type())
        return build_dpdk_apps(folder, extra_options)

    def build_dpdk_apps_linux(self, folder, extra_options):
        return self.send_expect("make -j -C %s %s" % (folder, extra_options),
                                "# ", 90)

    def build_dpdk_apps_freebsd(self, folder, extra_options):
        return self.send_expect("make -j -C %s %s CC=gcc48" % (folder, extra_options),
                                "# ", 90)

    def create_blacklist_string(self, target, nic):
        create_blacklist_string = getattr(self, 'create_blacklist_string_%s' % self.get_os_type())
        return create_blacklist_string(target, nic)

    def create_blacklist_string_linux(self, target, nic):
        blacklist = ''
        dutPorts = self.get_ports(nic)
        self.restore_interfaces()
        self.send_expect('insmod ./%s/kmod/igb_uio.ko' % target, '# ')
        self.bind_interfaces_linux()
        for port in range(0, len(self.ports_info)):
            if(port not in dutPorts):
                blacklist += '-b 0000:%s ' % self.ports_info[port]['pci']
        return blacklist

    def create_blacklist_string_freebsd(self, target, nic):
        blacklist = ''
        # No blacklist option in FreeBSD
        return blacklist


class DPDKtester(Tester):

    """
    DPDK project class for tester. DCTS will call prerequisites function to setup
    interface and generate port map.
    """

    def __init__(self, crb, serializer):
        self.NAME = "tester"
        super(DPDKtester, self).__init__(crb, serializer)

    def prerequisites(self, perf_test=False):
        self.kill_all()

        if not self.skip_setup:
            total_huge_pages = self.get_total_huge_pages()
            if total_huge_pages == 0:
                self.mount_huge_pages()
                self.set_huge_pages(1024)

            self.session.copy_file_to("tgen.tgz")
            # unpack tgen
            out = self.send_expect("tar zxf tgen.tgz", "# ")
            assert "Error" not in out

        self.send_expect("modprobe uio", "# ")

        self.tester_prerequisites()

        # use software pktgen for performance test
        if perf_test is True:
            try:
                if self.crb[IXIA] is not None:
                    self.logger.info("Use hardware packet generator")
            except Exception as e:
                self.logger.warning("Use default software pktgen")

            assert (os.path.isfile("/root/igb_uio.ko") is True), "Can not find igb_uio for performance"
            self.setup_memory()

    def setup_memory(self, hugepages=-1):
        hugepages_size = self.send_expect("awk '/Hugepagesize/ {print $2}' /proc/meminfo", "# ")

        if int(hugepages_size) < (1024 * 1024):
            arch_huge_pages = hugepages if hugepages > 0 else 1024
            total_huge_pages = self.get_total_huge_pages()

            self.mount_huge_pages()
            if total_huge_pages != arch_huge_pages:
                self.set_huge_pages(arch_huge_pages)
