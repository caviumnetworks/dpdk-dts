# BSD LICENSE
#
# Copyright(c) 2010-2016 Intel Corporation. All rights reserved.
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

Test the dynamic driver configuration feature.

"""

import utils

from test_case import TestCase

#
#
# Test class.
#


class TestDynamicConfig(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Dynamic config Prerequistites
        """

        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports(self.nic)

        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")

        # Prepare cores and ports
        cores = self.dut.get_core_list('1S/2C/2T')
        coreMask = utils.create_mask(cores)
        portMask = utils.create_mask(self.dut_ports[:2])

        # launch app
        cmd = "./%s/build/app/test-pmd/testpmd -c %s -n 3 -- -i --rxpt=0 \
        --rxht=0 --rxwt=0 --txpt=39 --txht=0 --txwt=0 --portmask=%s" % (self.target, self.coreMask, self.portMask)

        self.dut.send_expect("%s" % cmd, "testpmd> ", 120)

        # get dest address from self.target port
        out = self.dut.send_expect(
            "show port info %d" % self.dut_ports[0], "testpmd> ")

        self.dest = self.dut.get_mac_address(self.dut_ports[0])
        mac_scanner = r"MAC address: (([\dA-F]{2}:){5}[\dA-F]{2})"

        ret = utils.regexp(out, mac_scanner)

        self.verify(ret is not None, "MAC address not found")
        self.verify(cmp(ret.lower(), self.dest) == 0, "MAC address wrong")
        self.verify("Promiscuous mode: enabled" in out,
                    "wrong default promiscuous value")
        
        self.dut.kill_all()

    def dynamic_config_send_packet(self, portid, destMac="00:11:22:33:44:55"):
        """
        Send 1 packet to portid
        """

        itf = self.tester.get_interface(self.tester.get_local_port(portid))

        self.tester.scapy_foreground()
        self.tester.scapy_append(
            'sendp([Ether(dst="%s", src="52:00:00:00:00:00")/Raw(load="X"*26)], iface="%s")' % (destMac, itf))

        self.tester.scapy_execute()

    def set_up(self):
        """
        Run before each test case.
        """
        cmd = "./%s/build/app/test-pmd/testpmd -c %s -n 3 -- -i --rxpt=0 \
        --rxht=0 --rxwt=0 --txpt=39 --txht=0 --txwt=0 --portmask=%s" % (self.target, self.coreMask, self.portMask)

        self.dut.send_expect("%s" % cmd, "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ", 120)


    def test_dynamic_config_default_mode(self):
        """
        Dynamic config default mode test
        """

        portid = self.dut_ports[0]

        # get the current rx statistic
        out = self.dut.send_expect("clear port stats all" , "testpmd> ")
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        # send one packet with different MAC address than the portid
        self.dynamic_config_send_packet(portid)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        # check the pakcet increasment
        self.verify(int(cur_rxpkt) == int(pre_rxpkt)
                    + 1, "1st packet increasement check error")

        # send one packet with the portid MAC address
        self.dynamic_config_send_packet(portid, self.dest)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        # check the pakcet increasment
        self.verify(int(cur_rxpkt) == int(pre_rxpkt)
                    + 1, "2nd packet increasement check error")

    def test_dynamic_config_disable_promiscuous(self):
        """
        Dynamic config disable promiscuous test
        """

        portid = self.dut_ports[0]

        self.dut.send_expect("set promisc all off", "testpmd> ")
        out = self.dut.send_expect(
             "show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        self.dynamic_config_send_packet(portid)
        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect(
              "show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")
        self.verify(int(cur_rxpkt) == int(
              pre_rxpkt), "1st packet increasment error")
        self.dynamic_config_send_packet(portid, self.dest)
        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect(
              "show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")
        self.verify(int(cur_rxpkt) == int(
              pre_rxpkt) + 1, "2nd packet increasment error")

    def test_dynamic_config_broadcast(self):
        """
        Dynamic config disable promiscuous, send a broadcast packet
        dpdk will received packet and fwd by io model. send a general packet
        and dst mac not port mac, dpdk will not received packet.
        """
        
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("set fwd io", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd> ")

        
        self.dynamic_config_send_packet(self.dut_ports[0],"ff:ff:ff:ff:ff:ff")
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
          
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")
        self.verify(int(cur_rxpkt) == 1, "not received broadcast packet")
          
        self.dut.send_expect("clear port stats all", "testpmd> ")

        self.dynamic_config_send_packet(self.dut_ports[0])
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
          
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")
        self.verify(int(cur_rxpkt) == 0, "disable promisc, received a dst mac not match packet")

    def test_dynamic_config_allmulticast(self):
        """
        Dynamic config disable promiscuous,when dpdk enable multicast, send a 
        mulicast packet, dpdk received this packet and fwd by io model. when dpdk
        disable multicast, dpdk not received this packet
        """

        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("set fwd io", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd> ")
        self.dut.send_expect("set allmulti all on", "testpmd> ")
        
        self.dynamic_config_send_packet(self.dut_ports[0],"01:00:00:33:00:01")
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
            
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")
        self.verify(int(cur_rxpkt) == 1, "enable allmulti switch, not received allmulti packet")
           
        self.dut.send_expect("clear port stats all", "testpmd> ")
        self.dut.send_expect("set allmulti all off", "testpmd> ")
        
        self.dynamic_config_send_packet(self.dut_ports[0],"01:00:00:33:00:01")
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
 
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")
        self.verify(int(cur_rxpkt) == 0, "disable allmulti switch, received allmulti packet")
           
    def test_dynamic_config_enable_promiscuous(self):
        """
        Dynamic config enable promiscuous test
        """

        portid = self.dut_ports[0]

        self.dut.send_expect("set promisc %d on" % portid, "testpmd> ")

        # get the current rx statistic
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        # send one packet with different MAC address than the portid
        self.dynamic_config_send_packet(portid)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        # check the pakcet increasment
        self.verify(int(cur_rxpkt) == int(pre_rxpkt)
                    + 1, "1st packet increasment error")

        # send one packet with the portid MAC address
        self.dynamic_config_send_packet(portid, self.dest)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % self.dut_ports[1], "testpmd> ")
        cur_rxpkt = utils.regexp(out, "TX-packets: ([0-9]+)")

        # check the pakcet increasment
        self.verify(int(cur_rxpkt) == int(pre_rxpkt)
                    + 1, "2nd packet increasment error")

        #self.dut.send_expect("quit", "# ", 30)

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()
        
    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
