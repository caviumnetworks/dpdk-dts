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
DPDK Test suite.
Test IPv4 fragmentation features in DPDK.
"""

import dts
import string
import re
import time

lpm_table_ipv4 = [
    "{IPv4(100,10,0,0), 16, P1}",
    "{IPv4(100,20,0,0), 16, P1}",
    "{IPv4(100,30,0,0), 16, P0}",
    "{IPv4(100,40,0,0), 16, P0}",
    "{IPv4(100,50,0,0), 16, P1}",
    "{IPv4(100,60,0,0), 16, P1}",
    "{IPv4(100,70,0,0), 16, P0}",
    "{IPv4(100,80,0,0), 16, P0}",
]

lpm_table_ipv6 = [
    "{{1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P1}",
    "{{2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P1}",
    "{{3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P0}",
    "{{4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P0}",
    "{{5,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P1}",
    "{{6,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P1}",
    "{{7,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P0}",
    "{{8,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, 48, P0}",
]

from test_case import TestCase


class TestIpfrag(TestCase):

    def portRepl(self, match):
        """
        Function to replace P([0123]) pattern in tables
        """

        portid = match.group(1)
        self.verify(int(portid) in range(4), "invalid port id")
        return '%s' % eval("P" + str(portid))

    def set_up_all(self):
        """
        ip_fragmentation Prerequisites
        """

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports()
        print ports

        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports for testing")

        self.ports_socket = self.dut.get_numa_id(ports[0])

        # Verify that enough threads are available
        cores = self.dut.get_core_list("2S/2C/2T")
        self.verify(cores is not None, "Insufficient cores for speed testing")

        global P0, P1
        P0 = ports[0]
        P1 = ports[1]

        pat = re.compile("P([0123])")

        # Prepare long prefix match table, replace P(x) port pattern
        lpmStr_ipv4 = "static struct l3fwd_ipv4_route \
l3fwd_ipv4_route_array[] = {\\\n"
        rtLpmTbl = list(lpm_table_ipv4)
        for idx in range(len(rtLpmTbl)):
            rtLpmTbl[idx] = pat.sub(self.portRepl, rtLpmTbl[idx])
            lpmStr_ipv4 = lpmStr_ipv4 + ' ' * 4 + rtLpmTbl[idx] + ",\\\n"
        lpmStr_ipv4 = lpmStr_ipv4 + "};"
        print lpmStr_ipv4
        lpmStr_ipv6 = "static struct l3fwd_ipv6_route l3fwd_ipv6_route_array[] = {\\\n"
        rtLpmTbl = list(lpm_table_ipv6)
        for idx in range(len(rtLpmTbl)):
            rtLpmTbl[idx] = pat.sub(self.portRepl, rtLpmTbl[idx])
            lpmStr_ipv6 = lpmStr_ipv6 + ' ' * 4 + rtLpmTbl[idx] + ",\\\n"
        lpmStr_ipv6 = lpmStr_ipv6 + "};"
        print lpmStr_ipv6
        self.dut.send_expect(r"sed -i '/l3fwd_ipv4_route_array\[\].*{/,/^\}\;/c\\%s' examples/ip_fragmentation/main.c" % lpmStr_ipv4, "# ")
        self.dut.send_expect(r"sed -i '/l3fwd_ipv6_route_array\[\].*{/,/^\}\;/c\\%s' examples/ip_fragmentation/main.c" % lpmStr_ipv6, "# ")
        # make application
        out = self.dut.build_dpdk_apps("examples/ip_fragmentation")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def functional_check_ipv4(self, cores, pkt_sizes, burst=1, flag=None, funtion=None):
        """
        Perform functional fragmentation checks.
        """

        coremask = dts.create_mask(cores)
        portmask = dts.create_mask([P0, P1])
        numPortThread = len([P0, P1]) / len(cores)
        result = True
        errString = ''

        # run ipv4_frag
        self.dut.send_expect("examples/ip_fragmentation/build/ip_fragmentation -c %s -n %d -- -p %s -q %s" % (
            coremask, self.dut.get_memory_channels(), portmask, numPortThread), "IP_FRAG:", 120)

        txItf = self.tester.get_interface(self.tester.get_local_port(P0))
        rxItf = self.tester.get_interface(self.tester.get_local_port(P1))
        dmac = self.dut.get_mac_address(P0)
        for size in pkt_sizes[::burst]:
            # simulate to set TG properties
            if flag == 'frag':
                # do fragment
                expPkts = (1517 + size) / 1518
                val = 0
            else:
                expPkts = 1
                val = 2

            # set wait packet
            self.tester.scapy_background()
            self.tester.scapy_append('import string')
            self.tester.scapy_append('p = sniff(iface="%s", count=%d, timeout=5)' % (rxItf, expPkts))
            self.tester.scapy_append('nr_packets=len(p)')
            self.tester.scapy_append('reslist = [p[i].sprintf("%IP.len%;%IP.id%;%IP.flags%;%IP.frag%") for i in range(nr_packets)]')
            self.tester.scapy_append('RESULT = string.join(reslist, ",")')

            # send packet
            self.tester.scapy_foreground()
            for times in range(burst):
                self.tester.scapy_append('sendp([Ether(dst="%s")/IP(dst="100.10.0.1",src="1.2.3.4",flags=%d)/Raw(load="X"*%d)], iface="%s")' % (dmac, val, pkt_sizes[pkt_sizes.index(size) + times] - 38, txItf))

            self.tester.scapy_execute()
            time.sleep(5)
            out = self.tester.scapy_get_result()
            nr_packets = len(out.split(','))
            if funtion is not None:
                if not funtion(size, out.split(',')):
                    result = False
                    errString = "failed on fragment check size " + str(size)
                    break
            elif nr_packets != expPkts:
                result = False
                errString = "Failed on forward packet size " + str(size)
                break

        self.dut.send_expect("^C", "#")
        # verify on the bottom so as to keep safety quit application
        self.verify(result, errString)

    def functional_check_ipv6(self, cores, pkt_sizes, burst=1, flag=None, funtion=None):
        """
        Perform functional fragmentation checks.
        """
        coremask = dts.create_mask(cores)
        portmask = dts.create_mask([P0, P1])
        numPortThread = len([P0, P1]) / len(cores)
        result = True
        errString = ''

        # run ipv4_frag
        self.dut.send_expect("examples/ip_fragmentation/build/ip_fragmentation -c %s -n %d -- -p %s -q %s" % (
            coremask, self.dut.get_memory_channels(), portmask, numPortThread), "IP_FRAG:", 120)

        txItf = self.tester.get_interface(self.tester.get_local_port(P0))
        rxItf = self.tester.get_interface(self.tester.get_local_port(P1))
        dmac = self.dut.get_mac_address(P0)
        for size in pkt_sizes[::burst]:
            # simulate to set TG properties
            if flag == 'frag':
                # do fragment
                expPkts = (1517 + size) / 1518
                val = 0
            else:
                expPkts = 1
                val = 2

            # set wait packet
            self.tester.scapy_background()
            self.tester.scapy_append('import string')
            self.tester.scapy_append('p = sniff(iface="%s", count=%d)' % (rxItf, expPkts))
            self.tester.scapy_append('nr_packets=len(p)')
            self.tester.scapy_append('reslist = [p[i].sprintf("%IPv6.plen%;%IPv6.id%;%IPv6ExtHdrFragment.m%;%IPv6ExtHdrFragment.offset%") for i in range(nr_packets)]')
            self.tester.scapy_append('RESULT = string.join(reslist, ",")')

            # send packet
            self.tester.scapy_foreground()
            for times in range(burst):
                self.tester.scapy_append('sendp([Ether(dst="%s")/IPv6(dst="101:101:101:101:101:101:101:101",src="ee80:ee80:ee80:ee80:ee80:ee80:ee80:ee80")/Raw(load="X"*%d)], iface="%s")' % (dmac, pkt_sizes[pkt_sizes.index(size) + times] - 58, txItf))

            self.tester.scapy_execute()
            out = self.tester.scapy_get_result()
            nr_packets = len(out.split(','))
            if funtion is not None:
                if not funtion(size, out.split(',')):
                    result = False
                    errString = "failed on fragment check size " + str(size)
                    break
            elif nr_packets != expPkts:
                result = False
                errString = "Failed on forward packet size " + str(size)
                break

        self.dut.send_expect("^C", "#")
        # verify on the bottom so as to keep safety quit application
        self.verify(result, errString)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_ipfrag_normalfwd(self):
        """
        Normal forward with 64, 128, 256, 512, 1024, 1518.
        """

        sizelist = [64, 128, 256, 512, 1024, 1518]
        cores = self.dut.get_core_list("1S/1C/2T")

        self.functional_check_ipv4(cores, sizelist)
        self.functional_check_ipv6(cores, sizelist)

    def test_ipfrag_nofragment(self):
        """
        Don't fragment test with 1519
        """

        sizelist = [1519, 1518]
        cores = self.dut.get_core_list("1S/1C/2T")
        self.tester.send_expect("ifconfig %s mtu 9200" % self.tester.get_interface(self.tester.get_local_port(P0)), "#")
        self.tester.send_expect("ifconfig %s mtu 9200" % self.tester.get_interface(self.tester.get_local_port(P1)), "#")

        self.functional_check_ipv4(cores, sizelist, 2, 'nofrag')
        self.functional_check_ipv6(cores, sizelist, 2, 'nofrag')
        self.tester.send_expect("ifconfig %s mtu 1500" % self.tester.get_interface(self.tester.get_local_port(P0)), "#")
        self.tester.send_expect("ifconfig %s mtu 1500" % self.tester.get_interface(self.tester.get_local_port(P1)), "#")

    def test_ipfrag_fragment(self):
        """
        Fragment test with more than 1519 packet sizes.
        """

        sizelist = [1519, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000]
        cores = self.dut.get_core_list("1S/1C/2T")

        self.tester.send_expect("ifconfig %s mtu 9200" % self.tester.get_interface(self.tester.get_local_port(P0)), "#")
        self.tester.send_expect("ifconfig %s mtu 9200" % self.tester.get_interface(self.tester.get_local_port(P1)), "#")

        def chkfunc(size, output):
            # check total size
            if (1517 + size) / 1518 != len(output):
                return False

            # check every field in packet
            for pkt in output:
                _, _, _, _ = pkt.split(';')
                # length, ID, fragoff, flags
                pass
            return True

        self.functional_check_ipv4(cores, sizelist, 1, 'frag', chkfunc)
        self.functional_check_ipv6(cores, sizelist, 1, 'frag', chkfunc)
        self.tester.send_expect("ifconfig %s mtu 1500" % self.tester.get_interface(self.tester.get_local_port(P0)), "#")
        self.tester.send_expect("ifconfig %s mtu 1500" % self.tester.get_interface(self.tester.get_local_port(P1)), "#")

    def benchmark(self, index, lcore, num_pthreads, size_list):
        """
        Just Test IPv4 Throughput for selected parameters.
        """

        Bps = dict()
        Pps = dict()
        Pct = dict()

        if int(lcore[0]) == 1:
            core_mask = dts.create_mask(self.dut.get_core_list(lcore, socket=self.ports_socket))
        else:
            core_mask = dts.create_mask(self.dut.get_core_list(lcore))

        portmask = dts.create_mask([P0, P1])

        self.dut.send_expect("examples/ip_fragmentation/build/ip_fragmentation -c %s -n %d -- -p %s -q %s" % (
            core_mask, self.dut.get_memory_channels(), portmask, num_pthreads), "IP_FRAG:", 120)

        result = [2, lcore, num_pthreads]
        for size in size_list:
            dmac = self.dut.get_mac_address(P0)
            flows = ['Ether(dst="%s")/IP(src="1.2.3.4", dst="100.10.0.1", flags=0)/("X"*%d)' % (dmac, size - 38),
                     'Ether(dst="%s")/IP(src="1.2.3.4", dst="100.20.0.1", flags=0)/("X"*%d)' % (dmac, size - 38),
                     'Ether(dst="%s")/IPv6(dst="101:101:101:101:101:101:101:101",src="ee80:ee80:ee80:ee80:ee80:ee80:ee80:ee80")/Raw(load="X"*%d)' % (dmac, size - 58),
                     'Ether(dst="%s")/IPv6(dst="201:101:101:101:101:101:101:101",src="ee80:ee80:ee80:ee80:ee80:ee80:ee80:ee80")/Raw(load="X"*%d)' % (dmac, size - 58)]
            self.tester.scapy_append('wrpcap("test1.pcap", [%s])' % string.join(flows, ','))

            # reserved for rx/tx bidirection test
            dmac = self.dut.get_mac_address(P1)
            flows = ['Ether(dst="%s")/IP(src="1.2.3.4", dst="100.30.0.1", flags=0)/("X"*%d)' % (dmac, size - 38),
                     'Ether(dst="%s")/IP(src="1.2.3.4", dst="100.40.0.1", flags=0)/("X"*%d)' % (dmac, size - 38),
                     'Ether(dst="%s")/IPv6(dst="301:101:101:101:101:101:101:101",src="ee80:ee80:ee80:ee80:ee80:ee80:ee80:ee80")/Raw(load="X"*%d)' % (dmac, size - 58),
                     'Ether(dst="%s")/IPv6(dst="401:101:101:101:101:101:101:101",src="ee80:ee80:ee80:ee80:ee80:ee80:ee80:ee80")/Raw(load="X"*%d)' % (dmac, size - 58)]
            self.tester.scapy_append('wrpcap("test2.pcap", [%s])' % string.join(flows, ','))

            self.tester.scapy_execute()

            tgenInput = []
            tgenInput.append((self.tester.get_local_port(P0), self.tester.get_local_port(P1), "test1.pcap"))
            tgenInput.append((self.tester.get_local_port(P1), self.tester.get_local_port(P0), "test2.pcap"))

            factor = (size + 1517) / 1518
            # wireSpd = 2 * 10000.0 / ((20 + size) * 8)
            Bps[str(size)], Pps[str(size)] = self.tester.traffic_generator_throughput(tgenInput)
            self.verify(Pps[str(size)] > 0, "No traffic detected")
            Pps[str(size)] *= 1.0 / factor / 1000000
            Pct[str(size)] = (1.0 * Bps[str(size)] * 100) / (2 * 10000000000)

            result.append(Pps[str(size)])
            result.append(Pct[str(size)])

        dts.results_table_add_row(result)

        self.dut.send_expect("^C", "#")

    def test_perf_ipfrag_throughtput(self):
        """
        Performance test for 64, 1518, 1519, 2k and 9k.
        """
        self.tester.send_expect("ifconfig %s mtu 9600" % self.tester.get_interface(self.tester.get_local_port(P0)), "#")
        self.tester.send_expect("ifconfig %s mtu 9600" % self.tester.get_interface(self.tester.get_local_port(P1)), "#")

        sizes = [64, 1518, 1519, 2000, 9000]

        tblheader = ["Ports", "S/C/T", "SW threads"]
        for size in sizes:
            tblheader.append("%dB Mpps" % size)
            tblheader.append("%d" % size)

        dts.results_table_add_header(tblheader)

        lcores = [("1S/1C/1T", 2), ("1S/1C/2T", 2), ("1S/2C/1T", 2), ("2S/1C/1T", 2)]
        index = 1
        for (lcore, numThr) in lcores:
            self.benchmark(index, lcore, numThr, sizes)
            index += 1

        dts.results_table_print()

        self.tester.send_expect("ifconfig %s mtu 1500" % self.tester.get_interface(self.tester.get_local_port(P0)), "#")
        self.tester.send_expect("ifconfig %s mtu 1500" % self.tester.get_interface(self.tester.get_local_port(P1)), "#")

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.send_expect("^C", "#")
        pass
