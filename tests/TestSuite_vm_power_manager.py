# BSD LICENSE
#
# Copyright(c) 2010-2015 Intel Corporation. All rights reserved.
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
DPDK Test suite.
VM power manager test suite.
"""

import re
import utils
from test_case import TestCase
from etgen import IxiaPacketGenerator
from settings import HEADER_SIZE
from qemu_libvirt import LibvirtKvm


class TestVmPowerManager(TestCase, IxiaPacketGenerator):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2,
                    "Not enough ports for " + self.nic)

        # create temporary folder for power monitor
        self.dut.send_expect("mkdir -p /tmp/powermonitor", "# ")
        self.dut.send_expect("chmod 777 /tmp/powermonitor", "# ")
        # compile vm power manager
        out = self.dut.build_dpdk_apps("./examples/vm_power_manager")
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")

        # map between host vcpu and guest vcpu
        self.vcpu_map = []
        # start vm
        self.vm_name = "vm0"
        self.vm = LibvirtKvm(self.dut, self.vm_name, self.suite)
        channels = [
            {'path': '/tmp/powermonitor/%s.0' %
                self.vm_name, 'name': 'virtio.serial.port.poweragent.0'},
            {'path': '/tmp/powermonitor/%s.1' %
                self.vm_name, 'name': 'virtio.serial.port.poweragent.1'},
            {'path': '/tmp/powermonitor/%s.2' %
                self.vm_name, 'name': 'virtio.serial.port.poweragent.2'},
            {'path': '/tmp/powermonitor/%s.3' %
                self.vm_name, 'name': 'virtio.serial.port.poweragent.3'}
        ]
        for channel in channels:
            self.vm.add_vm_virtio_serial_channel(**channel)

        self.vm_dut = self.vm.start()

        # ping cpus
        cpus = self.vm.get_vm_cpu()
        self.vcpu_map = cpus[:]
        self.core_num = len(cpus)

        # build guest cli
        out = self.vm_dut.build_dpdk_apps(
            "examples/vm_power_manager/guest_cli")
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")

        self.vm_power_dir = "./examples/vm_power_manager/"
        mgr_cmd = self.vm_power_dir + "build/vm_power_mgr -c 0x3 -n 4"
        out = self.dut.send_expect(mgr_cmd, "vmpower>", 120)
        self.verify("Initialized successfully" in out,
                    "Power manager failed to initialized")
        self.dut.send_expect("add_vm %s" % self.vm_name, "vmpower>")
        self.dut.send_expect("add_channels %s all" % self.vm_name, "vmpower>")
        vm_info = self.dut.send_expect("show_vm %s" % self.vm_name, "vmpower>")

        # performance measure
        self.frame_sizes = [128]
        self.perf_rates = [0, 20, 40, 60, 80, 100]
        self.def_framesize = 64

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_managment_channel(self):
        """
        Check power monitor channel connection
        """
        # check Channels and vcpus
        guest_cmd = self.vm_power_dir + \
            "guest_cli/build/guest_vm_power_mgr -c 0xf -n 4 -- -i"
        out = self.vm_dut.send_expect(guest_cmd, "vmpower\(guest\)>", 120)
        self.verify("now connected" in out,
                    "Power manager guest failed to connect")
        self.vm_dut.send_expect("quit", "# ")

    def get_cpu_frequency(self, core_id):
        cpu_regex = ".*\nCore (\d+) frequency: (\d+)"
        out = self.dut.send_expect("show_cpu_freq %s" % core_id, "vmpower>")
        m = re.match(cpu_regex, out)
        freq = -1
        if m:
            freq = int(m.group(2))

        return freq

    def test_vm_power_managment_freqdown(self):
        """
        Check host cpu frequency can scale down in VM
        """
        guest_cmd = self.vm_power_dir + \
            "guest_cli/build/guest_vm_power_mgr -c 0xf -n 4 -- -i"
        out = self.vm_dut.send_expect(guest_cmd, "vmpower\(guest\)>", 120)
        self.verify("now connected" in out,
                    "Power manager guest failed to connect")

        for vcpu in range(self.core_num):
            self.vm_dut.send_expect(
                "set_cpu_freq %d max" % vcpu, "vmpower\(guest\)>")

        for vcpu in range(self.core_num):
            # map between host cpu and guest cpu
            ori_freq = self.get_cpu_frequency(self.vcpu_map[vcpu])
            # get cpu frequencies range
            freqs = self.get_cpu_freqs(vcpu)

            for loop in range(len(freqs)-1):
                # connect vm power host and guest
                self.vm_dut.send_expect(
                    "set_cpu_freq %d down" % vcpu, "vmpower\(guest\)>")
                cur_freq = self.get_cpu_frequency(self.vcpu_map[vcpu])
                print utils.GREEN("After freqency down, freq is %d\n" % cur_freq)
                self.verify(
                    ori_freq > cur_freq, "Cpu freqenecy can not scale down")
                ori_freq = cur_freq

        self.vm_dut.send_expect("quit", "# ")

    def test_vm_power_managment_frequp(self):
        """
        Check host cpu frequency can scale up in VM
        """
        guest_cmd = self.vm_power_dir + \
            "guest_cli/build/guest_vm_power_mgr -c 0xf -n 4 -- -i"
        out = self.vm_dut.send_expect(guest_cmd, "vmpower\(guest\)>", 120)
        self.verify("now connected" in out,
                    "Power manager guest failed to connect")

        for vcpu in range(self.core_num):
            self.vm_dut.send_expect(
                "set_cpu_freq %d min" % vcpu, "vmpower\(guest\)>")

        for vcpu in range(self.core_num):
            ori_freq = self.get_cpu_frequency(self.vcpu_map[vcpu])
            # get cpu frequencies range
            freqs = self.get_cpu_freqs(vcpu)
            for loop in range(len(freqs)-1):
                self.vm_dut.send_expect(
                    "set_cpu_freq %d up" % vcpu, "vmpower\(guest\)>")
                cur_freq = self.get_cpu_frequency(self.vcpu_map[vcpu])
                print utils.GREEN("After freqency up, freq is %d\n" % cur_freq)
                self.verify(
                    cur_freq > ori_freq, "Cpu freqenecy can not scale up")
                ori_freq = cur_freq

        self.vm_dut.send_expect("quit", "# ")

    def test_vm_power_managment_freqmax(self):
        """
        Check host cpu frequency can scale to max in VM
        """
        guest_cmd = self.vm_power_dir + \
            "guest_cli/build/guest_vm_power_mgr -c 0xf -n 4 -- -i"
        out = self.vm_dut.send_expect(guest_cmd, "vmpower\(guest\)>", 120)
        self.verify("now connected" in out,
                    "Power manager guest failed to connect")

        max_freq_path = "cat /sys/devices/system/cpu/cpu%s/cpufreq/" + \
                        "cpuinfo_max_freq"
        for vcpu in range(self.core_num):
            self.vm_dut.send_expect(
                "set_cpu_freq %d max" % vcpu, "vmpower\(guest\)>")
            freq = self.get_cpu_frequency(self.vcpu_map[vcpu])

            out = self.dut.alt_session.send_expect(
                max_freq_path % self.vcpu_map[vcpu], "# ")
            max_freq = int(out)

            self.verify(freq == max_freq, "Cpu max frequency not correct")
            print utils.GREEN("After freqency max, freq is %d\n" % max_freq)
        self.vm_dut.send_expect("quit", "# ")

    def test_vm_power_managment_freqmin(self):
        """
        Check host cpu frequency can scale to min in VM
        """
        guest_cmd = self.vm_power_dir + \
            "guest_cli/build/guest_vm_power_mgr -c 0xf -n 4 -- -i"
        out = self.vm_dut.send_expect(guest_cmd, "vmpower\(guest\)>", 120)
        self.verify("now connected" in out,
                    "Power manager guest failed to connect")

        min_freq_path = "cat /sys/devices/system/cpu/cpu%s/cpufreq/" + \
                        "cpuinfo_min_freq"
        for vcpu in range(self.core_num):
            self.vm_dut.send_expect(
                "set_cpu_freq %d min" % vcpu, "vmpower\(guest\)>")
            freq = self.get_cpu_frequency(self.vcpu_map[vcpu])

            out = self.dut.alt_session.send_expect(
                min_freq_path % self.vcpu_map[vcpu], "# ")
            min_freq = int(out)

            self.verify(freq == min_freq, "Cpu min frequency not correct")
            print utils.GREEN("After freqency min, freq is %d\n" % min_freq)
        self.vm_dut.send_expect("quit", "# ")

    def test_vm_power_multivms(self):
        """
        Check power management channel connected in multiple VMs
        """
        vm_name = "vm1"
        cpus = self.dut.get_core_list('1S/4C/1T', socket=1)
        self.verify(len(cpus) == 4, "Can't allocate cores from numa 1")

        vm2 = LibvirtKvm(self.dut, vm_name, self.suite)
        channels = [
            {'path': '/tmp/powermonitor/%s.0' %
                vm_name, 'name': 'virtio.serial.port.poweragent.0'},
            {'path': '/tmp/powermonitor/%s.1' %
                vm_name, 'name': 'virtio.serial.port.poweragent.1'},
            {'path': '/tmp/powermonitor/%s.2' %
                vm_name, 'name': 'virtio.serial.port.poweragent.2'},
            {'path': '/tmp/powermonitor/%s.3' %
                vm_name, 'name': 'virtio.serial.port.poweragent.3'}
        ]
        for channel in channels:
            vm2.add_vm_virtio_serial_channel(**channel)

        # start vm2 with socket 1 cpus
        cpupin = ''
        for cpu in cpus:
            cpupin += '%s ' % cpu
        vm2_cpus = {'number': '4', 'cpupin': cpupin[:-1]}
        vm2.set_vm_cpu(**vm2_cpus)
        vm2_dut = vm2.start()

        self.dut.send_expect("add_vm %s" % vm_name, "vmpower>")
        self.dut.send_expect("add_channels %s all" % vm_name, "vmpower>")
        vm_info = self.dut.send_expect("show_vm %s" % vm_name, "vmpower>")

        # check host core has correct mapped
        cpu_idx = 0
        for cpu in cpus:
            mask = utils.create_mask([cpu])
            cpu_map = '[%d]: Physical CPU Mask %s' % (cpu_idx, mask)
            self.verify(cpu_map in vm_info, "Faile to map host cpu %s" % cpu)
            cpu_idx += 1

        out = vm2_dut.build_dpdk_apps("examples/vm_power_manager/guest_cli")
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")

        guest_cmd = self.vm_power_dir + \
            "guest_cli/build/guest_vm_power_mgr -c 0xf -n 4 -- -i"
        out = vm2_dut.send_expect(guest_cmd, "vmpower\(guest\)>", 120)
        self.verify("now connected" in out,
                    "Power manager guest failed to connect")
        vm2_dut.send_expect("quit", "# ")
        vm2.stop()

    def test_perf_vmpower_latency(self):
        """
        Measure packet latency in VM
        """
        latency_header = ['Frame Size', 'Max latency', 'Min lantecy',
                          'Avg latency']

        self.result_table_create(latency_header)

        rx_port = self.dut_ports[0]
        tx_port = self.dut_ports[1]

        # build l3fwd-power
        out = self.vm_dut.send_expect("make -C examples/l3fwd-power", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")
        # start l3fwd-power
        l3fwd_app = "./examples/l3fwd-power/build/l3fwd-power"

        cmd = l3fwd_app + " -c 6 -n 4 -- -p 0x3 --config " + \
                          "'(0,0,1),(1,0,2)'"

        self.vm_dut.send_expect(cmd, "L3FWD_POWER: entering main loop")

        for frame_size in self.frame_sizes:
            # Prepare traffic flow
            payload_size = frame_size - HEADER_SIZE['udp'] - \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth']
            dmac = self.dut.get_mac_address(self.dut_ports[0])
            flow = 'Ether(dst="%s")/IP(dst="2.1.1.0")/UDP()' % dmac + \
                   '/Raw("X"*%d)' % payload_size
            self.tester.scapy_append('wrpcap("vmpower.pcap", [%s])' % flow)
            self.tester.scapy_execute()

            tgen_input = []
            tgen_input.append((self.tester.get_local_port(rx_port),
                              self.tester.get_local_port(tx_port),
                              "vmpower.pcap"))
            # run traffic generator
            [latency] = self.tester.traffic_generator_latency(tgen_input)
            print latency
            table_row = [frame_size, latency['max'], latency['min'],
                         latency['average']]
            self.result_table_add(table_row)

        self.result_table_print()

        self.vm_dut.kill_all()

    def test_perf_vmpower_frequency(self):
        """
        Measure cpu frequency fluctuate with work load
        """
        latency_header = ['Tx linerate%', 'Rx linerate%', 'Cpu freq']

        self.result_table_create(latency_header)

        rx_port = self.dut_ports[0]
        tx_port = self.dut_ports[1]

        # build l3fwd-power
        out = self.vm_dut.send_expect("make -C examples/l3fwd-power", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")
        # start l3fwd-power
        l3fwd_app = "./examples/l3fwd-power/build/l3fwd-power"

        cmd = l3fwd_app + " -c 6 -n 4 -- -p 0x3 --config " + \
                          "'(0,0,1),(1,0,2)'"

        self.vm_dut.send_expect(cmd, "L3FWD_POWER: entering main loop")

        for rate in self.perf_rates:
            # Prepare traffic flow
            payload_size = self.def_framesize - HEADER_SIZE['udp'] - \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth']
            dmac = self.dut.get_mac_address(self.dut_ports[0])
            flow = 'Ether(dst="%s")/IP(dst="2.1.1.0")/UDP()' % dmac + \
                   '/Raw("X"*%d)' % payload_size
            self.tester.scapy_append('wrpcap("vmpower.pcap", [%s])' % flow)
            self.tester.scapy_execute()

            tgen_input = []
            tgen_input.append((self.tester.get_local_port(rx_port),
                              self.tester.get_local_port(tx_port),
                              "vmpower.pcap"))

            # register hook function for current cpu frequency
            self.hook_transmissoin_func = self.get_freq_in_transmission
            self.tester.extend_external_packet_generator(TestVmPowerManager,
                                                         self)
            # run traffic generator, run 20 seconds for frequency stable
            _, pps = self.tester.traffic_generator_throughput(tgen_input,
                                                              rate,
                                                              delay=20)
            pps /= 1000000.0
            freq = self.cur_freq / 1000000.0
            wirespeed = self.wirespeed(self.nic, self.def_framesize, 1)
            pct = pps * 100 / wirespeed
            table_row = [rate, pct, freq]
            self.result_table_add(table_row)

        self.result_table_print()

        self.vm_dut.kill_all()

    def get_freq_in_transmission(self):
        self.cur_freq = self.get_cpu_frequency(self.vcpu_map[1])
        print utils.GREEN("Current cpu frequency %d" % self.cur_freq)

    def get_max_freq(self, core_num):
        freq_path = "cat /sys/devices/system/cpu/cpu%d/cpufreq/" + \
                    "cpuinfo_max_freq"

        out = self.dut.alt_session.send_expect(freq_path % core_num, "# ")
        freq = int(out)
        return freq

    def get_min_freq(self, core_num):
        freq_path = "cat /sys/devices/system/cpu/cpu%d/cpufreq/" + \
                    "cpuinfo_min_freq"

        out = self.dut.alt_session.send_expect(freq_path % core_num, "# ")
        freq = int(out)
        return freq

    def get_cpu_freqs(self, core_num):
        freq_path = "cat /sys/devices/system/cpu/cpu%d/cpufreq/" + \
                    "scaling_available_frequencies"

        out = self.dut.alt_session.send_expect(freq_path % core_num, "# ")
        freqs = out.split()
        return freqs

    def tear_down(self):
        """
        Run after each test case.
        """
        self.vm_dut.send_expect("quit", "# ")
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.send_expect("quit", "# ")
        self.vm.stop()
        pass
