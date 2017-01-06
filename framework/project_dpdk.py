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

from settings import NICS, load_global_setting, accepted_nic
from settings import DPDK_RXMODE_SETTING, HOST_DRIVER_SETTING
from ssh_connection import SSHConnection
from crb import Crb
from dut import Dut
from tester import Tester
from logger import getLogger
from settings import IXIA, DRIVERS


class DPDKdut(Dut):

    """
    DPDK project class for DUT. DTS will call set_target function to setup
    build, memory and kernel module.
    """

    def __init__(self, crb, serializer):
        super(DPDKdut, self).__init__(crb, serializer)
        self.testpmd = None

    def set_target(self, target, bind_dev=True):
        """
        Set env variable, these have to be setup all the time. Some tests
        need to compile example apps by themselves and will fail otherwise.
        Set hugepage on DUT and install modules required by DPDK.
        Configure default ixgbe PMD function.
        """
        self.target = target
        self.set_toolchain(target)

        # set env variable
        # These have to be setup all the time. Some tests need to compile
        # example apps by themselves and will fail otherwise.
        self.send_expect("export RTE_TARGET=" + target, "#")
        self.send_expect("export RTE_SDK=`pwd`", "#")

        self.set_rxtx_mode()

        # Enable MLNX driver before installing dpdk
        drivername = load_global_setting(HOST_DRIVER_SETTING)
        if drivername == DRIVERS['ConnectX4']:
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_MLX5_PMD=n/"
                             + "CONFIG_RTE_LIBRTE_MLX5_PMD=y/' config/common_base", "# ", 30)

        if not self.skip_setup:
            self.build_install_dpdk(target)

        self.setup_memory()
        self.setup_modules(target)

        if bind_dev and self.get_os_type() == 'linux':
            self.bind_interfaces_linux(drivername)
        self.extra_nic_setup()

    def setup_modules(self, target):
        """
        Install DPDK required kernel module on DUT.
        """
        setup_modules = getattr(self, 'setup_modules_%s' % self.get_os_type())
        setup_modules(target)

    def setup_modules_linux(self, target):
        drivername = load_global_setting(HOST_DRIVER_SETTING)
        if drivername == "vfio-pci":
            self.send_expect("rmmod vfio_pci", "#", 70)
            self.send_expect("rmmod vfio_iommu_type1", "#", 70)
            self.send_expect("rmmod vfio", "#", 70)
            self.send_expect("modprobe vfio", "#", 70)
            self.send_expect("modprobe vfio-pci", "#", 70)
            out = self.send_expect("lsmod | grep vfio_iommu_type1", "#")
            assert ("vfio_iommu_type1" in out), "Failed to setup vfio-pci"
        else:
            self.send_expect("modprobe uio", "#", 70)
            out = self.send_expect("lsmod | grep igb_uio", "#")
            if "igb_uio" in out:
                self.send_expect("rmmod -f igb_uio", "#", 70)
            self.send_expect("insmod ./" + target + "/kmod/igb_uio.ko", "#", 60)

            out = self.send_expect("lsmod | grep igb_uio", "#")
            assert ("igb_uio" in out), "Failed to insmod igb_uio"

    def setup_modules_freebsd(self, target):
        """
        Install DPDK required Freebsd kernel module on DUT.
        """
        binding_list = ''

        for (pci_bus, pci_id) in self.pci_devices_info:
            if accepted_nic(pci_id):
                binding_list += '%s,' % (pci_bus)

        self.send_expect("kldunload if_ixgbe.ko", "#")
        self.send_expect('kenv hw.nic_uio.bdfs="%s"' % binding_list[:-1], '# ')
        self.send_expect("kldload ./%s/kmod/nic_uio.ko" % target, "#", 20)
        out = self.send_expect("kldstat", "#")
        assert ("nic_uio" in out), "Failed to insmod nic_uio"

    def set_rxtx_mode(self):
        """
        Set default RX/TX PMD function,
        only i40e support scalar/full RX/TX model.
        ixgbe and fm10k only support vector and no vector model
        all NIC default rx/tx model is vector PMD
        """

        mode = load_global_setting(DPDK_RXMODE_SETTING)
        if mode == 'scalar':
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_I40E_INC_VECTOR=.*$/"
                             + "CONFIG_RTE_LIBRTE_I40E_INC_VECTOR=n/' config/common_base", "# ", 30)
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_I40E_RX_ALLOW_BULK_ALLOC=.*$/"
                             + "CONFIG_RTE_LIBRTE_I40E_RX_ALLOW_BULK_ALLOC=y/' config/common_base", "# ", 30)
        if mode == 'full':
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_I40E_INC_VECTOR=.*$/"
                             + "CONFIG_RTE_LIBRTE_I40E_INC_VECTOR=n/' config/common_base", "# ", 30)
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_I40E_RX_ALLOW_BULK_ALLOC=.*$/"
                             + "CONFIG_RTE_LIBRTE_I40E_RX_ALLOW_BULK_ALLOC=n/' config/common_base", "# ", 30)
        if mode == 'novector':
            self.send_expect("sed -i -e 's/CONFIG_RTE_IXGBE_INC_VECTOR=.*$/"
                             + "CONFIG_RTE_IXGBE_INC_VECTOR=n/' config/common_base", "# ", 30)
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_I40E_INC_VECTOR=.*$/"
                             + "CONFIG_RTE_LIBRTE_I40E_INC_VECTOR=n/' config/common_base", "# ", 30)
            self.send_expect("sed -i -e 's/CONFIG_RTE_LIBRTE_FM10K_INC_VECTOR=.*$/"
                             + "CONFIG_RTE_LIBRTE_FM10K_INC_VECTOR=n/' config/common_base", "# ", 30)

    def set_package(self, pkg_name="", patch_list=[]):
        self.package = pkg_name
        self.patches = patch_list

    def build_install_dpdk(self, target, extra_options=''):
        """
        Build DPDK source code with specified target.
        """
        build_install_dpdk = getattr(self, 'build_install_dpdk_%s' % self.get_os_type())
        build_install_dpdk(target, extra_options)

    def build_install_dpdk_linux(self, target, extra_options):
        """
        Build DPDK source code on linux with specified target.
        """
        build_time = 300
        if "icc" in target:
            build_time = 900
        # clean all
        self.send_expect("rm -rf " + target, "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_c.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_tar.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_pci_sysfs.res.o' , "#")

        # compile
        out = self.send_expect("make -j install T=%s %s" % (target, extra_options), "# ", build_time)

        if("Error" in out or "No rule to make" in out):
            self.logger.error("ERROR - try without '-j'")
            # if Error try to execute make without -j option
            out = self.send_expect("make install T=%s %s" % (target, extra_options), "# ", 120)

        assert ("Error" not in out), "Compilation error..."
        assert ("No rule to make" not in out), "No rule to make error..."

    def build_install_dpdk_freebsd(self, target, extra_options):
        """
        Build DPDK source code on Freebsd with specified target.
        """
        # clean all
        self.send_expect("rm -rf " + target, "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_c.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_tar.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_pci_sysfs.res.o' , "#")

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

    def prepare_package(self):
        if not self.skip_setup:
            assert (os.path.isfile(self.package) is True), "Invalid package"

            p_dir, _ = os.path.split(self.base_dir)
            # ToDo: make this configurable
            dst_dir = "/tmp/"

            out = self.send_expect("ls %s && cd %s" % (dst_dir, p_dir),
                                   "#", verify=True)
            if out == -1:
                raise ValueError("Directiry %s or %s does not exist,"
                                 "please check params -d"
                                 % (p_dir, dst_dir))
            self.session.copy_file_to(self.package, dst_dir)

            # put patches to p_dir/patches/
            if (self.patches is not None):
                for p in self.patches:
                    self.session.copy_file_to('dep/' + p, dst_dir)

            self.kill_all()

            # enable core dump
            self.send_expect("ulimit -c unlimited", "#")

            # unpack the code and change to the working folder
            self.send_expect("rm -rf %s" % self.base_dir, "#")

            # unpack dpdk
            out = self.send_expect("tar zxf %s%s -C %s" %
                                   (dst_dir, self.package.split('/')[-1], p_dir),
                                   "# ", 20, verify=True)
            if out == -1:
                raise ValueError("Extract dpdk package to %s failure,"
                                 "please check params -d"
                                 % (p_dir))

            # check dpdk dir name is expect
            out = self.send_expect("ls %s" % self.base_dir,
                                   "# ", 20, verify=True)
            if out == -1:
                raise ValueError("dpdk dir %s mismatch, please check params -d"
                                 % self.base_dir)

            if (self.patches is not None):
                for p in self.patches:
                    out = self.send_expect("patch -d %s -p1 < %s" %
                                           (self.base_dir, dst_dir + p), "# ")
                    assert "****" not in out

    def prerequisites(self):
        """
        Copy DPDK package to DUT and apply patch files.
        """
        self.prepare_package()
        self.dut_prerequisites()
        self.stage = "post-init"

    def extra_nic_setup(self):
        """
        Some nic like RRC required additional setup after module installed
        """
        for port_info in self.ports_info:
            netdev = port_info['port']
            netdev.setup()

    def bind_interfaces_linux(self, driver='igb_uio', nics_to_bind=None):
        """
        Bind the interfaces to the selected driver. nics_to_bind can be None
        to bind all interfaces or an array with the port indexes
        """
        binding_list = '--bind=%s ' % driver

        current_nic = 0
        for port_info in self.ports_info:
            if nics_to_bind is None or current_nic in nics_to_bind:
                binding_list += '%s ' % (port_info['pci'])
            current_nic += 1

        self.send_expect('usertools/dpdk-devbind.py %s' % binding_list, '# ')

    def unbind_interfaces_linux(self, nics_to_bind=None):
        """
        Unbind the interfaces
        """

        binding_list = '-u '

        current_nic = 0
        for port_info in self.ports_info:
            if nics_to_bind is None or current_nic in nics_to_bind:
                binding_list += '%s ' % (port_info['pci'])
            current_nic += 1

        self.send_expect('usertools/dpdk-devbind.py %s' % binding_list, '# ', 30)

    def build_dpdk_apps(self, folder, extra_options=''):
        """
        Build dpdk sample applications.
        """
        build_dpdk_apps = getattr(self, 'build_dpdk_apps_%s' % self.get_os_type())
        return build_dpdk_apps(folder, extra_options)

    def build_dpdk_apps_linux(self, folder, extra_options):
        """
        Build dpdk sample applications on linux.
        """
        # icc compile need more time
        if 'icc' in self.target:
            timeout = 300
        else:
            timeout = 90
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_c.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_tar.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_pci_sysfs.res.o' , "#")
        return self.send_expect("make -j -C %s %s" % (folder, extra_options),
                                "# ", timeout)

    def build_dpdk_apps_freebsd(self, folder, extra_options):
        """
        Build dpdk sample applications on Freebsd.
        """
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_c.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_resource_tar.res.o' , "#")
        self.send_expect("rm -rf %s" % r'./app/test/test_pci_sysfs.res.o' , "#")
        return self.send_expect("make -j -C %s %s CC=gcc48" % (folder, extra_options),
                                "# ", 180)

    def get_blacklist_string(self, target, nic):
        """
        Get black list command string.
        """
        get_blacklist_string = getattr(self, 'get_blacklist_string_%s' % self.get_os_type())
        return get_blacklist_string(target, nic)

    def get_blacklist_string_linux(self, target, nic):
        """
        Get black list command string on Linux.
        """
        blacklist = ''
        dutPorts = self.get_ports(nic)
        self.restore_interfaces()
        self.send_expect('insmod ./%s/kmod/igb_uio.ko' % target, '# ')
        self.bind_interfaces_linux()
        for port in range(0, len(self.ports_info)):
            if(port not in dutPorts):
                blacklist += '-b %s ' % self.ports_info[port]['pci']
        return blacklist

    def get_blacklist_string_freebsd(self, target, nic):
        """
        Get black list command string on Freebsd.
        """
        blacklist = ''
        # No blacklist option in FreeBSD
        return blacklist


class DPDKtester(Tester):

    """
    DPDK project class for tester. DTS will call prerequisites function to setup
    interface and generate port map.
    """

    def __init__(self, crb, serializer):
        self.NAME = "tester"
        super(DPDKtester, self).__init__(crb, serializer)

    def prerequisites(self, perf_test=False):
        """
        Setup hugepage on tester and copy validation required files to tester.
        """
        self.kill_all()

        if not self.skip_setup:
            total_huge_pages = self.get_total_huge_pages()
            if total_huge_pages == 0:
                self.mount_huge_pages()
                self.set_huge_pages(1024)

            self.session.copy_file_to("dep/tgen.tgz")
            self.session.copy_file_to("dep/tclclient.tgz")
            # unpack tgen
            out = self.send_expect("tar zxf tgen.tgz", "# ")
            assert "Error" not in out
            # unpack tclclient
            out = self.send_expect("tar zxf tclclient.tgz", "# ")
            assert "Error" not in out

        self.send_expect("modprobe uio", "# ")

        self.tester_prerequisites()

        self.set_promisc()
        # use software pktgen for performance test
        if perf_test is True:
            try:
                if self.crb[IXIA] is not None:
                    self.logger.info("Use hardware packet generator")
            except Exception as e:
                self.logger.warning("Use default software pktgen")
                out = self.send_expect("ls /root/igb_uio.ko", "# ")
                assert ("No such file or directory" not in out), "Can not find /root/igb_uio.ko for performance"
                self.setup_memory()

        self.stage = "post-init"

    def setup_memory(self, hugepages=-1):
        """
        Setup hugepage on tester.
        """
        hugepages_size = self.send_expect("awk '/Hugepagesize/ {print $2}' /proc/meminfo", "# ")

        if int(hugepages_size) < (2048 * 2048):
            arch_huge_pages = hugepages if hugepages > 0 else 2048
            total_huge_pages = self.get_total_huge_pages()

        self.mount_huge_pages()
        if total_huge_pages != arch_huge_pages:
            self.set_huge_pages(arch_huge_pages)
