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
DPDK Test suite
Test DPDK vhost + virtio scenarios
"""
import re
import dts
import time

from test_case import TestCase
from qemu_kvm import QEMUKvm

class TestVirtioIperf(TestCase):
    def set_up_all(self):
        self.vhost_legacy_virtio_cmdline="csum=off,gso=off,guest_csum=off,guest_tso4=off,guest_tso6=off,guest_ecn=off"
        self.vhost_cuse_virtio_cmdline="csum=off,gso=off,guest_csum=off,guest_tso4=off,guest_tso6=off,guest_ecn=off"
        self.vhost_user_virtio_cmdline=""
        self.virtio_mac = ["52:54:00:00:00:01", "52:54:00:00:00:02"]
        self.virtio_ip = ["1.1.1.2", "1.1.1.3"]
        self.vm = []
        self.vm_dut = []

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, 'Insufficient ports for test')
        
        self.phy_function = self.dut_ports[0]
        netdev = self.dut.ports_info[self.phy_function]['port']
        self.socket = netdev.get_nic_socket()
        self.cores = self.dut.get_core_list("1S/3C/1T", socket=self.socket)
        self.coremask = dts.create_mask(self.cores)
        
    def set_up(self):
        pass
    
    def dut_execut_cmd(self, cmdline, ex='#', timout=30):
        return self.dut.send_expect(cmdline, ex, timout)
    
    def build_vhost_lib(self, vhost='user'):
        self.dut_execut_cmd('git clean -x -d -f')
        self.dut_execut_cmd('git checkout *')
        if vhost == 'cuse':
            self.dut_execut_cmd(
                "sed -i -e 's/CONFIG_RTE_LIBRTE_VHOST_USER=.*$/CONFIG_RTE_LIBRTE" +
                "_VHOST_USER=n/' ./config/common_linuxapp")
        else:
            self.dut_execut_cmd(
                "sed -i -e 's/CONFIG_RTE_LIBRTE_VHOST_USER=.*$/CONFIG_RTE_LIBRTE" +
                "_VHOST_USER=y/' ./config/common_linuxapp")
        self.dut.build_install_dpdk(self.target)
        self.dut_execut_cmd("cd ./lib/librte_vhost")
        out = self.dut_execut_cmd("make")
        self.verify('Error' not in out, 'bulid err: build lib vhost failed')
        self.dut_execut_cmd("cd ./eventfd_link")
        out = self.dut_execut_cmd("make")
        self.verify('Error' not in out, 'bulid err: build eventfd_link failed')
        self.dut_execut_cmd("cd ~/dpdk")
        
    def build_vhost_app(self):
        if self.nic in "niantic":
            self.dut_execut_cmd(
                "sed -i -e 's/define MAX_QUEUES.*/define MAX_QUEUES 128/' " +
                "./examples/vhost/main.c")
        else:
            self.dut_execut_cmd(
                "sed -i -e 's/define MAX_QUEUES.*/define MAX_QUEUES 512/' " +
                "./examples/vhost/main.c")
        out = self.dut_execut_cmd("make -C ./examples/vhost")
        self.verify("Error" not in out, "compilation error")
        self.verify("No such file" not in out, "Not found file error")
        
    def launch_vhost_switch(self, coremask, channel, jumbo, scenario):
        self.vhost_switch = "./examples/vhost/build/vhost-switch"
        self.vhost_switch_cmd = self.vhost_switch + \
        " -c %s -n %d --socket-mem 2048,2048 -- -p 0x1" + \
        " --mergeable %d --zero-copy 0 --vm2vm %d  > ./vhost.out &"
        self.dut_execut_cmd(self.vhost_switch_cmd % (coremask, channel, jumbo, scenario))
        time.sleep(20)
        self.dut.session.copy_file_from('/root/dpdk/vhost.out')
        time.sleep(5)
        fp = open('./vhost.out')
        fmsg = fp.read()
        fp.close()
        if 'Error' or 'error' in fmsg:
            print 'launch vhost sample failed'
            return False
        else:
            return True 

    def iperf_result_verify(self, vm_client):
        '''
        vm_client.session.copy_file_from("/root/dpdk/iperf_client.log")
        self.tester.send_expect('scp -P')
        '''
        vm_client.session.copy_file_from("/root/dpdk/iperf_client.log")
        fp = open("./iperf_client.log")
        fmsg = fp.read()
        iperfdata = re.compile('[\d+]*.[\d+] [M|G]bits/sec').findall(fmsg)
        dts.results_table_add_header(['Data', 'Unit'])
        for data in iperfdata:
            dts.results_table_add_row([data.split()[0], data.split()[1]])
        dts.results_table_print()
        import os
        os.popen("rm -rf ./iperf_client.log")
        
    def test_perf_vhost_legacy_virtio_iperf(self):
        pass

    def test_perf_vhost_cuse_virtio_iperf(self):
        """
        vhost cuse as back end, legacy virtio dirver as front end
        """
        self.build_vhost_lib(vhost='cuse')
        self.build_vhost_app()
        self.dut_execut_cmd('rm -rf /dev/vhost-net')
        self.dut_execut_cmd('rmmod igb_uio -f')
        self.dut_execut_cmd('rmmod eventfd_link')
        self.dut_execut_cmd('modprobe uio')
        self.dut_execut_cmd('modprobe fuse')
        self.dut_execut_cmd('modprobe cuse')
        self.dut_execut_cmd('insmod ./x86_64-native-linuxapp-gcc/kmod/igb_uio.ko')
        self.dut_execut_cmd('insmod ./lib/librte_vhost/eventfd_link/eventfd_link.ko')
        self.dut.bind_interfaces_linux(dts.drivername)
        self.launch_vhost_switch(self.coremask, 4, 0, 1)

        self.vm1 = QEMUKvm(self.dut, 'vm0', 'virtio_iperf')
        vm1_params = {}
        vm1_params['driver'] = 'vhost-cuse'
        vm1_params['opt_tap'] = 'vhost0'
        vm1_params['opt_mac'] = self.virtio_mac[0]
        vm1_params['opt_settings'] = self.vhost_cuse_virtio_cmdline
        self.vm1.set_vm_device(**vm1_params)
        try:
            self.vm1_dut = self.vm1.start(auto_portmap=False)
            time.sleep(10)
            if self.vm1_dut is None:
                raise Exception('VM1 start failed')
        except Exception as e0:
            print dts.RED('VM1 already exist, powerdown it first')
        self.vm1_dut.restore_interfaces()
        
        self.vm2 = QEMUKvm(self.dut, 'vm1', 'virtio_iperf')
        vm2_params = {}
        vm2_params['driver'] = 'vhost-cuse'
        vm2_params['opt_tap'] = 'vhost1'
        vm2_params['opt_mac'] = self.virtio_mac[1]
        vm2_params['opt_settings'] = self.vhost_cuse_virtio_cmdline
        self.vm2.set_vm_device(**vm2_params)
        try:
            self.vm2_dut = self.vm2.start(auto_portmap=False)
            time.sleep(10)
            if self.vm2_dut is None:
                raise Exception('VM2 start failed')
        except Exception as e1:
            print dts.RED('VM2 already exist, powerdown it first')
        self.vm2_dut.restore_interfaces()
        
        #self.start_iperf_server()
        vm1_vport = self.vm1_dut.send_expect('ifconfig -a', '#', 30)
        print 'vm net port:'
        print vm1_vport
        intfs = re.compile('eth\d').findall(vm1_vport)
        for intf in intfs:
            outmac = self.vm1_dut.send_expect('ifconfig %s' % intf, '#', 30)
            if self.virtio_mac[0] in outmac:
                self.vm1_intf = intf
        self.vm1_dut.send_expect('ifconfig %s %s' % (self.vm1_intf, self.virtio_ip[0]), '#', 10)
        self.vm1_dut.send_expect('ifconfig %s up' % self.vm1_intf, '#', 10)
        self.vm1_dut.send_expect('arp -s %s %s' % (self.virtio_ip[1], self.virtio_mac[1]), '#', 10)
        self.vm1_dut.send_expect('iperf -s -p 12345 -i 1 > iperf_server.log &', '', 10)
        
        #self.start_iperf_client()
        vm2_vport = self.vm2_dut.send_expect('ifconfig -a', '#', 30)
        print 'vm net port:'
        print vm2_vport
        intfs = re.compile('eth\d').findall(vm2_vport)
        for intf in intfs:
            outmac = self.vm2_dut.send_expect('ifconfig %s' % intf, '#', 30)
            if self.virtio_mac[1] in outmac:
                self.vm2_intf = intf
        self.vm2_dut.send_expect('ifconfig %s %s' % (self.vm2_intf, self.virtio_ip[1]), '#', 10)
        self.vm2_dut.send_expect('ifconfig %s up' % self.vm2_intf, '#', 10)
        self.vm2_dut.send_expect('arp -s %s %s' % (self.virtio_ip[0], self.virtio_mac[0]), '#', 10)
        self.vm2_dut.send_expect('iperf -c %s -p 12345 -i 1 -t 60 > iperf_client.log &' % self.virtio_ip[0], '', 60)
        time.sleep(70)
        self.vm1_dut.send_expect("killall -s INT iperf", '', 10)
        self.iperf_result_verify(self.vm2_dut)
        
    def test_perf_vhost_user_virtio_iperf(self):
        """
        vhost user as back end, legacy virtio dirver as front end
        """
        self.build_vhost_lib(vhost='user')
        self.build_vhost_app()
        #self.dut_execut_cmd('rm -rf /dev/vhost-net')
        self.dut_execut_cmd('rmmod igb_uio -f')
        self.dut_execut_cmd('rmmod eventfd_link')
        self.dut_execut_cmd('modprobe uio')
        #self.dut_execut_cmd('modprobe fuse')
        #self.dut_execut_cmd('modprobe cuse')
        self.dut_execut_cmd('insmod ./x86_64-native-linuxapp-gcc/kmod/igb_uio.ko')
        self.dut_execut_cmd('insmod ./lib/librte_vhost/eventfd_link/eventfd_link.ko')
        self.dut.bind_interfaces_linux(dts.drivername)
        self.launch_vhost_switch(self.coremask, 4, 0, 1)
        
        self.vm1 = QEMUKvm(self.dut, 'vm0', 'virtio_iperf')
        vm1_params = {}
        vm1_params['driver'] = 'vhost-user'
        vm1_params['opt_path'] = './vhost-net'
        vm1_params['opt_mac'] = self.virtio_mac[0]
        self.vm1.set_vm_device(**vm1_params)
        try:
            self.vm1_dut = self.vm1.start(auto_portmap=False)
            if self.vm1_dut is None:
                raise Exception('VM1 start failed')
        except Exception as e0:
            print dts.RED('VM1 already exist, powerdown it first')
        self.vm1_dut.restore_interfaces()

        self.vm2 = QEMUKvm(self.dut, 'vm1', 'virtio_iperf')
        vm2_params = {}
        vm2_params['driver'] = 'vhost-user'
        vm2_params['opt_path'] = './vhost-net'
        vm2_params['opt_mac'] = self.virtio_mac[1]
        self.vm2.set_vm_device(**vm2_params)
        try:
            self.vm2_dut = self.vm2.start(auto_portmap=False)
            if self.vm2_dut is None:
                raise Exception('VM2 start failed')
        except Exception as e1:
            print dts.RED('VM2 already exist, powerdown it first')
        
        self.vm2_dut.restore_interfaces()
        
        #self.start_iperf_server()
        vm1_vport = self.vm1_dut.send_expect('ifconfig -a', '#', 30)
        print 'vm net port:'
        print vm1_vport
        intfs = re.compile('eth\d').findall(vm1_vport)
        for intf in intfs:
            outmac = self.vm1_dut.send_expect('ifconfig %s' % intf, '#', 30)
            if self.virtio_mac[0] in outmac:
                self.vm1_intf = intf
        self.vm1_dut.send_expect('ifconfig %s %s' % (self.vm1_intf, self.virtio_ip[0]), '#', 10)
        self.vm1_dut.send_expect('ifconfig %s up' % self.vm1_intf, '#', 10)
        self.vm1_dut.send_expect('arp -s %s %s' % (self.virtio_ip[1], self.virtio_mac[1]), '#', 10)
        self.vm1_dut.send_expect('iperf -s -p 12345 -i 1 > iperf_server.log &', '', 10)
        
        #self.start_iperf_client()
        vm2_vport = self.vm2_dut.send_expect('ifconfig -a', '#', 30)
        print 'vm net port:'
        print vm2_vport
        intfs = re.compile('eth\d').findall(vm2_vport)
        for intf in intfs:
            outmac = self.vm2_dut.send_expect('ifconfig %s' % intf, '#', 30)
            if self.virtio_mac[1] in outmac:
                self.vm2_intf = intf
        self.vm2_dut.send_expect('ifconfig %s %s' % (self.vm2_intf, self.virtio_ip[1]), '#', 10)
        self.vm2_dut.send_expect('ifconfig %s up' % self.vm2_intf, '#', 10)
        self.vm2_dut.send_expect('arp -s %s %s' % (self.virtio_ip[0], self.virtio_mac[0]), '#', 10)
        self.vm2_dut.send_expect('iperf -c %s -p 12345 -i 1 -t 60 > iperf_client.log &' % self.virtio_ip[0], '', 60)
        time.sleep(70)
        
        self.vm1_dut.session.send_expect('killall -s INT iperf', '#', 10)
        self.iperf_result_verify(self.vm2_dut)
    
    def tear_down(self):
        if self.vm2:
            self.vm2.stop()
            self.vm2 = None
        if self.vm1:
            self.vm1.stop()
            self.vm1 = None
        self.dut.send_expect("killall -s INT vhost-switch", "#")

    def tear_down_all(self):
        pass
