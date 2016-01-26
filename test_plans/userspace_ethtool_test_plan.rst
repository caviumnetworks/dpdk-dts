.. Copyright (c) <2015> Intel Corporation
   All rights reserved.

   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:

   - Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.

   - Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in
     the documentation and/or other materials provided with the
     distribution.

   - Neither the name of Intel Corporation nor the names of its
     contributors may be used to endorse or promote products derived
     from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
   FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
   COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
   SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
   HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
   STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
   OF THE POSSIBILITY OF SUCH DAMAGE.

==================
 Userspace Ethtool
==================

This feature is designed to provide one rte_ethtool shim layer based on 
rte_ethdev API. The implementation also along with a command prompt driven
demonstration application. It only contained of 18 popular used Ethtool and
Netdevice ops as described in rte_ethtool.h.

Prerequisites
=============

Assume port 0 and 1 are connected to the traffic generator, to run the test
application in linuxapp environment with 4 lcores, 2 ports.

	ethtool -c f -n 4

The sample should be validated on Forville, Niantic and i350 Nics. 

Test Case: Dump driver infor test
=================================
User "drvinfo" command to dump driver information and then check that dumped
information was exactly the same as fact.

	EthApp> drvinfo
	Port 0 driver: rte_ixgbe_pmd (ver: RTE 2.1.0)
	Port 1 driver: rte_ixgbe_pmd (ver: RTE 2.1.0)

Use "link" command to dump all ports link status.
	EthApp> link
	Port 0: Up
	Port 1: Up

Change tester port link status to down and re-check link status.
	EthApp> link
	Port 0: Down
	Port 1: Down

Send few packets to l2fwd and check that command "portstats" dumped correct
port statistics.
    EthApp> portstats 0
    Port 0 stats
       In: 1 (64 bytes)
      Out: 1 (64 bytes)

Test Case: Retrieve eeprom test
===============================
Unbind ports from igb_uio and bind them to default driver.
Dump eeprom binary by ethtool.

ethtool --eeprom-dump INTF_0 raw on > ethtool_eeprom_0.bin
ethtool --eeprom-dump INTF_1 raw on > ethtool_eeprom_1.bin

Retrieve eeprom on specified port and compare csum with the file dumped by ethtool.

	EthApp> eeprom 0 eeprom_0.bin
	EthApp> eeprom 1 eeprom_1.bin

md5sum ethtool_eeprom_0.bin
md5sum eeprom_0.bin > eeprom_0.bin
	
diff ethtool_eeprom_0.hex eeprom_0.hex

Test Case: Retrieve register test
===============================
Retrieve register on specified port, do not known how to check the binary?

	EthApp> regs 0 reg_0.bin
	EthApp> regs 1 reg_1.bin	

Unbind ports from igb_uio and bind them to default driver.
Check that dumped register information is correct.

ethtool -d INTF_0 raw on file reg_0.bin
ethtool -d INTF_1 raw on file reg_0.bin
	
Test Case: Ring param test
==========================
Dump port 0 ring size by ringparam command and check numbers are correct.

EthApp> ringparam  0
Port 0 ring paramaeters
  Rx Pending: 128 (256 max)
  Tx Pending: 4096 (4096 max)

Change port 0 ring size by ringparam command and then verify Rx/Tx function.

EthApp> ringparam  0 256 2048

Recheck ring size by ringparam command.

EthApp> ringparam  0
Port 0 ring paramaeters
  Rx Pending: 256 (256 max)
  Tx Pending: 2048 (4096 max)
	
Test Case: Pause test
=====================
Enable port 0 Rx pause frame and then create two packets flows in IXIA port.
One flow is 100000 normally packet and the second flow is pause frame.
Check that port 0 Rx speed dropped. For example, niantic will drop from
14.8Mpps to 7.49Mpps.

	EthApp> pause 0 rx

Use "parse" command to print port pause status, check that port 0 rx has been
paused.
	EthApp> pause 0
	Port 0: Rx Paused

Unpause port 0 rx and then restart port0, check that packets Rx speed is normal.
	EthApp> pause 0 none
    EthApp> 

Pause port 0 TX pause frame.
	EthApp> pause 0 tx

Use "parse" command to print port pause status, check that port 1 tx has been
paused.
    EthApp> pause 0
    Port 0: Tx Paused

Enable flow control in IXIA port and send packets from IXIA with line rate.
Check that IXIA receive flow control packets and IXIA transmit speed dropped.
IXIA Rx packets more then Tx packets to check that received pause frame.

Unpause port 0 tx and restart port 0. Then send packets to port0, check that
packets forwarded normally from port 0.
	EthApp> pause 0 none
    EthApp> stop 0
    EthApp> open 0

Test Case: Vlan test
====================
Add vlan 0 to port 0 and vlan 1 to port1, send packet without vlan to port0,1
Verify port0 and port1 recevied vlan packets
	EthApp> vlan 0 add 0
	VLAN vid 0 added

	EthApp> vlan 1 add 1
	VLAN vid 1 added
	
Send packet with vlan0,1 to port0&1. Verify port0 and port1 received vlan
packets

Send packet with vlan1,0 to port0&1. Verify port0 and port1 can not receive
vlan packets

Remove vlan 0,1 from port0&1, send packet with vlan0,1 to port0,1. Verify
port0 and port1 can not receive vlan packet.

    EthApp> vlan 0 del 0
	VLAN vid 0 removed
	EthApp> vlan 1 del 1
	VLAN vid 1 removed

Test Case: Mac address test
===========================
Use "macaddr" command to dump port mac address and then check that dumped
information is exactly the same as fact.
	EthApp> macaddr 0
	Port 0 MAC Address: XX:XX:XX:XX:XX:XX
	EthApp> macaddr 1
	Port 1 MAC Address: YY:YY:YY:YY:YY:YY

Check mulitcast macaddress will not be valided.
	EthApp> validate 01:00:00:00:00:00
	Address is not unicast

Check all zero macaddress will not be valided.	
	EthApp> validate 00:00:00:00:00:00
	Address is not unicast

Use "macaddr" command to change port mac address and then check mac changed.
	EthApp> validate 00:10:00:00:00:00
	Address is unicast

	EthApp> macaddr 0 00:10:00:00:00:00
	MAC address changed
	EthApp> macaddr 0
	Port 0 MAC Address: 00:10:00:00:00:00
	
Verified  mac adress in forwarded packets has been changed.

Test Case: Port config test
===========================
Use "stop" command to stop port0. Send packets to port0 and verify no packet
recevied.
	EthApp> stop 0
	
Use "open" command to re-enable port0. Send packets to port0 and verify
packets received and forwarded.
	EthApp> open 0


Test case: Mtu config test
==========================
Use "mtu" command to change port 0 mtu from default 1518 to 1000.

Send packet size over 1000 and check that packet will be detected as error.

    EthApp> mtu 0 1000
    Port 0 stats
       In: 0 (0 bytes)
      Out: 0 (0 bytes)
      Err: 1

Change mtu to default value and send packet size over 1000 and check that
packet will normally received.
