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

Test the support of Dual VLAN Offload Features by Poll Mode Drivers.

"""

import dts
import random
import re

txvlan = 3
outvlan = 1
invlan = 2

allResult = {"TX+OUTER+INNER": (txvlan, outvlan, invlan),
             "TX+INNER": (txvlan, invlan),
             "TX+OUTER": (txvlan, outvlan),
             "OUTER+INNER": (outvlan, invlan),
             "INNER": (invlan,),
             "OUTER": (outvlan,),
             "NONE": ("No",)
             }

stripCase = 0x1
filterCase = 0x2
qinqCase = 0x4
txCase = 0x8

vlanCaseDef = [0, stripCase, filterCase, filterCase | stripCase,
               qinqCase, qinqCase | stripCase, qinqCase | filterCase, qinqCase | filterCase | stripCase,
               txCase, txCase | stripCase, txCase | filterCase, txCase | filterCase | stripCase,
               txCase | qinqCase, txCase | qinqCase | stripCase, txCase | qinqCase | filterCase, txCase | qinqCase | filterCase | stripCase]

vlanCase = ["OUTER+INNER", "INNER", ("OUTER+INNER", "NONE"), ("INNER", "NONE"),
            "OUTER+INNER", "OUTER", ("NONE", "OUTER+INNER"), ("NONE", "OUTER"),
            "TX+OUTER+INNER", "TX+INNER", ("TX+OUTER+INNER", "NONE"), ("TX+INNER", "NONE"),
            "TX+OUTER+INNER", "TX+OUTER", ("NONE", "TX+OUTER+INNER"), ("NONE", "TX+OUTER")]


from test_case import TestCase
from pmd_output import PmdOutput


class TestDualVlan(TestCase):
    def set_up_all(self):
        """
        Run at the start of each test suite.

        Vlan Prerequistites
        """
        global dutRxPortId
        global dutTxPortId

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(self.nic)
        self.verify(len(ports) >= 2, "Insufficient ports")
        self.ports_socket = self.dut.get_numa_id(ports[0])

        cores = self.dut.get_core_list('1S/2C/2T')
        coreMask = dts.create_mask(cores)

        ports = self.dut.get_ports(self.nic)
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]

        portMask = dts.create_mask(valports[:2])

        dutRxPortId = valports[0]
        dutTxPortId = valports[1]

        self.pmdout = PmdOutput(self.dut)
        self.pmdout.start_testpmd("Default", "--portmask=%s" % portMask, socket=self.ports_socket)

        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.dut.send_expect("vlan set filter on all", "testpmd> ")
            self.dut.send_expect("set promisc all off", "testpmd> ")

        out = self.dut.send_expect("set fwd mac", "testpmd> ")
        self.verify('Set mac packet forwarding mode' in out, "set fwd mac error")
        out = self.dut.send_expect("start", "testpmd> ", 120)

    def start_tcpdump(self, rxItf):

        self.tester.send_expect("rm -rf ./getPackageByTcpdump.cap", "#")
        self.tester.send_expect("tcpdump -i %s -w ./getPackageByTcpdump.cap 2> /dev/null& " % rxItf, "#")

    def get_tcpdump_package(self):
        self.tester.send_expect("killall tcpdump", "#")
        return self.tester.send_expect("tcpdump -nn -e -v -r ./getPackageByTcpdump.cap", "#")

    def vlan_send_packet(self, *vid):
        """
        Send packet to portid
        """
        txPort = self.tester.get_local_port(dutRxPortId)
        rxPort = self.tester.get_local_port(dutTxPortId)

        txItf = self.tester.get_interface(txPort)
        rxItf = self.tester.get_interface(rxPort)
        mac = self.dut.get_mac_address(dutRxPortId)

        self.start_tcpdump(rxItf)
        vlanString = 'sendp([Ether(dst="%s")/' % mac
        for i in range(len(vid)):
            vlanString += "Dot1Q(id=0x8100,vlan=%s)/" % vid[i]
        vlanString += 'IP(len=46)],iface="%s")' % txItf

        self.tester.scapy_append(vlanString)

        self.tester.scapy_execute()

    def mode_config(self, **modeName):
        """
        Set up the VLAN mode.
        """

        for mode in modeName:
            if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
                # fortville NIC vlan filter can't close, if want close need remove rx_vlan
                if mode == "filter":
                    if modeName[mode] == "off":
                        self.dut.send_expect("rx_vlan add %s %s" % (outvlan, dutRxPortId), "testpmd> ")
                        continue
                    else:
                        self.dut.send_expect("rx_vlan rm %s %s" % (outvlan, dutRxPortId), "testpmd> ")
                        continue

            if mode == "stripq":
                self.dut.send_expect("vlan set %s %s %s,0" % (mode, modeName[mode], dutRxPortId), "testpmd> ")
            else:
                self.dut.send_expect("vlan set %s %s %s" % (mode, modeName[mode], dutRxPortId), "testpmd> ")

        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ")
        for mode in modeName:
            if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
                # fortville NIC vlan filter can't close, if want close need remove rx_vlan
                if mode == "filter":
                    if modeName[mode] == "off":
                        self.dut.send_expect("rx_vlan add %s %s" % (outvlan, dutRxPortId), "testpmd> ")
                        continue
                    else:
                        self.dut.send_expect("rx_vlan rm %s %s" % (outvlan, dutRxPortId), "testpmd> ")
                        continue

            if mode == "qinq":
                self.verify("qinq(extend) %s" % modeName[mode] in out, "%s setting error" % mode)
                continue
            elif mode == "stripq":
                continue
            else:
                self.verify("%s %s" % (mode, modeName[mode]) in out, "%s setting error" % mode)

    def multimode_test(self, caseIndex):
        """
        Setup Strip/Filter/Extend/Insert enable/disable for synthetic test.
        """
        caseDef = vlanCaseDef[caseIndex]
        temp = []

        temp.append("on") if (caseDef & stripCase) != 0 else temp.append("off")
        temp.append("on") if (caseDef & filterCase) != 0 else temp.append("off")
        temp.append("on") if (caseDef & qinqCase) != 0 else temp.append("off")
        self.mode_config(strip=temp[0], filter=temp[1], qinq=temp[2])

        if (caseDef & txCase) != 0:
            self.dut.send_expect('tx_vlan set %s %s' % (dutTxPortId, txvlan), "testpmd> ")

        configMode = "Strip %s, filter %s 0x1, extend %s, insert %s" % (temp[0], temp[1], temp[2], "on" if (caseDef & txCase) != 0 else "off")

        if (caseDef & filterCase) != 0:
            self.dut.send_expect('rx_vlan add %s %s' % (outvlan, dutRxPortId), "testpmd> ")
            self.vlan_send_packet(outvlan, invlan)
            self.check_result(vlanCase[caseIndex][0], configMode + " result Error")
            self.dut.send_expect('rx_vlan rm %s %s' % (outvlan, dutRxPortId), "testpmd> ")
            self.dut.send_expect('rx_vlan add %s %s' % (invlan, dutRxPortId), "testpmd> ")
            self.vlan_send_packet(outvlan, invlan)
            self.check_result(vlanCase[caseIndex][1], configMode + " result Error")
            self.dut.send_expect('rx_vlan rm %s %s' % (invlan, dutRxPortId), "testpmd> ")
            if (caseDef & txCase) != 0:
                self.dut.send_expect('tx_vlan reset %s' % dutTxPortId, "testpmd> ")
        else:
            self.dut.send_expect('rx_vlan add %s %s' % (invlan, dutRxPortId), "testpmd> ")
            self.dut.send_expect('rx_vlan add %s %s' % (outvlan, dutRxPortId), "testpmd> ")
            self.vlan_send_packet(outvlan, invlan)
            self.check_result(vlanCase[caseIndex], configMode + " result Error")
            if (caseDef & txCase) != 0:
                self.dut.send_expect('tx_vlan reset %s' % dutTxPortId, "testpmd> ")
            self.dut.send_expect('rx_vlan rm %s %s' % (invlan, dutRxPortId), "testpmd> ")
            self.dut.send_expect('rx_vlan rm %s %s' % (outvlan, dutRxPortId), "testpmd> ")

    def check_result(self, resultKey, errorString):
        """
        Check results of synthetic test.
        """
        print "vlan flage config:%s" % errorString
        out = self.get_tcpdump_package()
        if allResult[resultKey][0] == "No":
            self.verify("vlan" not in out, errorString)
        else:
            resultList = []
            for i in range(len(allResult[resultKey]) - 1):
                resultList.append("vlan %s" % allResult[resultKey][i])
            resultList.append("vlan %s" % allResult[resultKey][len(allResult[resultKey]) - 1])
            for line in resultList:
                self.verify(line in out, "reviceive package is wrong:%s" % out)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_vlan_filter_config(self):
        """
        Enable/Disable VLAN packets filtering
        """
        self.mode_config(filter="on")
        self.mode_config(strip="off")
        self.mode_config(qinq="off")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        print out
        self.verify(out is not None and "vlan %s" % outvlan not in out, "Vlan filter enable error: " + out)

        if self.nic not in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.mode_config(filter="off")
            self.vlan_send_packet(outvlan)
            out = self.get_tcpdump_package()
            self.verify("vlan %s" % outvlan in out, "Vlan filter disable error: " + out)
        else:
            self.dut.send_expect('rx_vlan add %s %s' % (outvlan, dutRxPortId), "testpmd> ")
            self.vlan_send_packet(outvlan)
            out = self.get_tcpdump_package()
            self.verify("vlan %s" % outvlan in out, "Vlan filter disable error: " + out)
            self.dut.send_expect('rx_vlan rm %s %s' % (outvlan, dutRxPortId), "testpmd> ")

    def test_vlan_filter_table(self):
        """
        Add/Remove VLAN Tag Identifier pass VLAN filtering
        """

        self.mode_config(filter="on")
        self.mode_config(strip="off")
        self.mode_config(qinq="off")

        self.dut.send_expect("rx_vlan add %s %s" % (outvlan, dutRxPortId), "testpmd> ")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan in out, "vlan filter table enable error: " + out)

        self.dut.send_expect("rx_vlan rm %s %s" % (outvlan, dutRxPortId), "testpmd> ")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify(out is not None and "vlan %s" % outvlan not in out, "vlan filter table disable error: " + out)

    def test_vlan_strip_config(self):
        """
        Enable/Disable VLAN packets striping
        """

        self.mode_config(filter="off")
        self.mode_config(qinq="off")
        self.mode_config(strip="on")
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.dut.send_expect('rx_vlan add %s %s' % (outvlan, dutRxPortId), "testpmd> ")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan not in out, "Vlan strip enable error: " + out)

        self.mode_config(strip="off")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan in out, "Vlan strip disable error: " + out)
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.dut.send_expect('rx_vlan rm %s %s' % (outvlan, dutRxPortId), "testpmd> ")

    def test_vlan_stripq_config(self):
        """
        Enable/Disable VLAN packets strip on queue
        """
        self.verify(self.nic not in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"], "%s NIC not support queue vlan strip " % self.nic)

        self.mode_config(filter="off")
        self.mode_config(qinq="off")
        self.mode_config(strip="off")
        self.mode_config(stripq="off")
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.dut.send_expect('rx_vlan add %s %s' % (outvlan, dutRxPortId), "testpmd> ")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan in out, "vlan strip queue disable error : " + out)
        # if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]:
        self.mode_config(strip="on")
        self.mode_config(stripq="on")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan not in out, "vlan strip enable error: " + out)

        self.mode_config(stripq="off")
        self.vlan_send_packet(outvlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan in out, "vlan strip queue disable error: " + out)
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.dut.send_expect('rx_vlan rm %s %s' % (outvlan, dutRxPortId), "testpmd> ")

    def test_vlan_insert_config(self):
        """
        Enable/Disable VLAN packets inserting
        """
        self.mode_config(filter="off")
        self.mode_config(qinq="off")

        # hartwell need to set CTRL.VME for vlan insert
        if(self.nic == "hartwell"):
            self.dut.send_expect("vlan set strip on %s" % dutTxPortId, "testpmd> ")

        self.dut.send_expect("tx_vlan set %s %s" % (dutTxPortId, txvlan), "testpmd> ")

        self.vlan_send_packet()
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % txvlan in out, "vlan inset enalber error: " + out)

        self.dut.send_expect("tx_vlan reset %s" % dutTxPortId, "testpmd> ")
        self.vlan_send_packet()
        out = self.get_tcpdump_package()
        self.verify("vlan %s" % txvlan not in out, "vlan inset disable error: " + out)

    def test_vlan_tpid_config(self):
        """
        Configure receive port out vlan TPID
        """
        self.verify(self.nic not in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV", "hartwell"], "%s NIC not support tcpid " % self.nic)

        self.mode_config(filter="on", strip="on", qinq="on")
        # nic only support inner model, except fortville nic
        self.dut.send_expect("vlan set inner tpid 1234 %s" % dutRxPortId, "testpmd> ")
        self.vlan_send_packet(outvlan, invlan)

        out = self.get_tcpdump_package()
        self.verify("vlan %s" % outvlan in out, "vlan tpid disable error: " + out)
        self.verify("vlan %s" % invlan in out, "vlan tpid disable error: " + out)

        self.dut.send_expect("vlan set inner tpid 0x8100 %s" % dutRxPortId, "testpmd> ")
        self.vlan_send_packet(outvlan, invlan)

        out = self.get_tcpdump_package()
        self.verify(out is not None and "vlan" not in out, "vlane tpid enable error: " + out)

    def test_vlan_synthetic_test(self):
        """
        VLAN synthetic test.
        """
        self.verify(self.nic != "hartwell", "sorry, dual vlan cannot support this self.nic")
        for i in range(len(vlanCase)):
            self.multimode_test(i)

    def test_vlan_random_test(self):
        """
        VLAN random test.
        """
        self.verify(self.nic != "hartwell", "sorry, dual vlan cannot support this self.nic")
        for _ in range(30):
            rand = random.randint(0, 15)
            self.multimode_test(rand)

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
        pass
