.. Copyright (c) <2014>, Intel Corporation
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

Bonding
=======

Provide the ability to support Link Bonding for 1GbE and 10GbE ports similar the ability found in Linux to allow the aggregation of multiple (slave) NICs into a single logical interface between a server and a switch. A new PMD will then process these interfaces based on the mode of operation specified and supported. This provides support for redundant links, fault tolerance and/or load balancing of networks. Bonding may also be used in connection with 802.1q VLAN support. 
The following is a good overview http://www.cyberciti.biz/howto/question/static/linux-ethernet-bonding-driver-howto.php

**Requirements**

* The Bonding mode SHOULD be specified via an API for a logical bonded interface used for link aggregation. 
* A new PMD layer SHALL operate on the bonded interfaces and may be used in connection with 802.1q VLAN support.
* Bonded ports SHALL maintain statistics similar to that of normal ports
* The slave links SHALL be monitor for link status change. See also the concept of up/down time delay to handle situations such as a switch reboots, it is possible that its ports report "link up" status before they become usable.
* The following bonding modes SHALL be available;

  - Mode = 0 (balance-rr) Round-robin policy: (default). Transmit packets in sequential order from the first available network interface (NIC) slave through the last. This mode provides load balancing and fault tolerance. Packets may be bulk dequeued from devices then serviced in round-robin manner. The order should be specified so that it corresponds to the other side.
 
  - Mode = 1 (active-backup) Active-backup policy: Only one NIC slave in the bond is active. A different slave becomes active if, and only if, the active slave fails. The single logical bonded interface's MAC address is externally visible on only one NIC (port) to avoid confusing the network switch. This mode provides fault tolerance. Active-backup policy is useful for implementing high availability solutions using two hubs
  
  - Mode = 2 (balance-xor) XOR policy: Transmit network packets based on the default transmit policy. The default policy (layer2) is a simple [(source MAC address XOR'd with destination MAC address) modulo slave count].  Alternate transmit policies may be selected. The default transmit policy selects the same NIC slave for each destination MAC address. This mode provides load balancing and fault tolerance.
  
  - Mode = 3 (broadcast) Broadcast policy: Transmit network packets on all slave network interfaces. This mode provides fault tolerance but is only suitable for special cases. 
  
  - Mode = 4 (802.3ad) IEEE 802.3ad Dynamic link aggregation. Creates aggregation groups that share the same speed and duplex settings. Utilizes all slaves in the active aggregator according to the 802.3ad specification. This mode requires a switch that supports IEEE 802.3ad Dynamic link aggregation. Slave selection for outgoing traffic is done according to the transmit hash policy, which may be changed from the default simple XOR layer2 policy.
  
  - Mode = 5 (balance-tlb) Adaptive transmit load balancing. Linux bonding driver mode that does not require any special network switch support. The outgoing network packet traffic is distributed according to the current load (computed relative to the speed) on each network interface slave. Incoming traffic is received by one currently designated slave network interface. If this receiving slave fails, another slave takes over the MAC address of the failed receiving slave.
  
  - Mode = 6 (balance-alb) Adaptive load balancing. Includes balance-tlb plus receive load balancing (rlb) for IPV4 traffic, and does not require any special network switch support. The receive load balancing is achieved by ARP negotiation. The bonding driver intercepts the ARP Replies sent by the local system on their way out and overwrites the source hardware address with the unique hardware address of one of the NIC slaves in the single logical bonded interface such that different network-peers use different MAC addresses for their network packet traffic.
* The available transmit policies SHALL be as follows;

  - layer2: Uses XOR of hardware MAC addresses to generate the hash.  The formula is (source MAC XOR destination MAC) modulo slave count. This algorithm will place all traffic to a particular network peer on the same slave. This algorithm is 802.3ad compliant.
  - layer3+4: This policy uses upper layer protocol information, when available, to generate the hash.  This allows for traffic to a particular network peer to span multiple slaves, although a single connection will not span multiple slaves.   The formula for unfragmented TCP and UDP packets is ((source port XOR dest port) XOR  ((source IP XOR dest IP) AND 0xffff)  modulo slave count.  For fragmented TCP or UDP packets and all other IP protocol traffic, the source and destination port information is omitted.  For non-IP traffic, the formula is the same as for the layer2 transmit hash policy. This policy is intended to mimic the behavior of certain switches, notably Cisco switches with PFC2 as well as some Foundry and IBM products. This algorithm is not fully 802.3ad compliant.  A single TCP or UDP conversation containing both fragmented and unfragmented packets will see packets striped across two interfaces.  This may result in out of order delivery.  Most traffic types will not meet these criteria, as TCP rarely fragments traffic, and most UDP traffic is not involved in extended conversations.  Other implementations of 802.3ad may or may not tolerate this noncompliance.
  
* Upon unbonding the bonding PMD driver MUST restore the MAC addresses that the slaves had before they were enslaved.
* According to the bond type, when the bond interface is placed in promiscuous mode it will propagate the setting to the slave devices as follow: For mode=0, 2, 3 and 4 the promiscuous mode setting is propagated to all slaves.
* Mode=0, 2, 3 generally require that the switch have the appropriate ports grouped together (e.g. Cisco 5500 series with EtherChannel support or may be called a trunk group).

* Goals: 

  - Provide a forwarding example that demonstrates Link Bonding for 2/4x 1GbE ports and 2x 10GbE with the ability to specify the links to be bound, the port order if required, and the bonding type to be used. MAC address of the bond MUST be settable or taken from its first slave device. The example SHALL also allow the enable/disable of promiscuous mode and disabling of the bonding resulting in the return of the normal interfaces and the ability to bring up and down the logical bonded link.  
  - Provide the performance for each of these modes.

This bonding test plan is mainly to test basic bonding APIs via testpmd and the supported modes(0-3) and each mode's performance in R1.7. 

Prerequisites for Bonding
=========================

* NIC and IXIA ports requriements.
  - Tester: have 4 10Gb (Niantic) ports and 4 1Gb ports. 
  - DUT: have 4 10Gb (Niantic) ports and 4 1Gb ports. All functional tests should be done on both 10G and 1G port.
  - IXIA: have 4 10G ports and 4 1G ports. IXIA is used for performance test.
* BIOS settings on DUT:
  - Enhanced Intel Speedstep----DISABLED
  - Processor C3--------------------DISABLED
  - Processor C6--------------------DISABLED
  - Hyper-Threading----------------ENABLED
  - Intel VT-d-------------------------DISABLED
  - MLC Streamer-------------------ENABLED
  - MLC Spatial Prefetcher--------ENABLED
  - DCU Data Prefetcher-----------ENABLED
  - DCU Instruction Prefetcher----ENABLED
  - Direct Cache Access(DCA)--------------------- ENABLED
  - CPU Power and Performance Policy-----------Performance
  - Memory Power Optimization---------------------Performance Optimized
  - Memory RAS and Performance Configuration-->NUMA Optimized----ENABLED  
* Connections ports between tester/ixia and DUT
  - TESTER(Or IXIA)-------DUT
  - portA------------------port0
  - portB------------------port1
  - portC------------------port2
  - portD------------------port3
  
   
Test Setup#1 for Functional test
================================

Tester has 4 ports(portA--portD), and DUT has 4 ports(port0-port3), then connect portA to port0, portB to port1, portC to port2, portD to port3. 


	 
Test Case1: Basic bonding--Create bonded devices and slaves
===========================================================

Use Setup#1.

Create bonded device, add first slave, verify default bonded device has default mode 0 and default primary slave.Below are the sample commands and output``
    
    ./app/testpmd -c f -n 4 -- -i
    .....
    Port 0 Link Up - speed 10000 Mbps - full-duplex
    Port 1 Link Up - speed 10000 Mbps - full-duplex
    Port 2 Link Up - speed 10000 Mbps - full-duplex
    Port 3 Link Up - speed 10000 Mbps - full-duplex
    Done
    testpmd> create bonded device 1 1(mode socket, if not set, default mode=0, default socket=0)
    Created new bonded device (Port 4)
    testpmd> add bonding slave 1 4
    Adding port 1 as slave
    testpmd> show bonding config 4
        Bonding mode: 1
        Slaves: [1]
        Active Slaves: []
        Failed to get primary slave for port=4
    testpmd> port start 4
    ......
    Done
    testpmd> show bonding config 4
        Bonding mode: 1
        Slaves: [1]
        Active Slaves: [1]
        Primary: [1]

Create another bonded device, and check if the slave added to bonded device1 can't be added to bonded device2.

    testpmd> create bonded device 1 1
    Created new bonded device (Port 5)
    testpmd> add bonding slave 0 4
    Adding port 0 as slave
    testpmd> add bonding slave 0 5
    Failed to add port 0 as slave

Change the bonding mode and verify if it works.

    testpmd> set bonding mode 3 4
    testpmd> show bonding config 4

Add 2nd slave, and change the primary slave to 2nd slave and verify if it works.

    testpmd> add bonding slave 2 4
    testpmd> set bonding primary 2 4
    testpmd> show bonding config 4  
    
Remove the slaves, and check the bonded device again. Below is the sample command.
    testpmd> remove bonding slave 1 4
    testpmd> show bonding config 4(Verify that slave1 is removed from slaves/active slaves).
    testpmd> remove bonding slave 0 4
    testpmd> remove bonding slave 2 4(This command can't be done, since bonded device need at least 1 slave)
    testpmd> show bonding config 4
 

Test Case2: Basic bonding--MAC Address Test
===========================================

Use Setup#1.

Create bonded device, add one slave, verify bonded device MAC address is the slave's MAC. 

    ./app/testpmd -c f -n 4 -- -i
    .....
    Port 0 Link Up - speed 10000 Mbps - full-duplex
    Port 1 Link Up - speed 10000 Mbps - full-duplex
    Port 2 Link Up - speed 10000 Mbps - full-duplex
    Port 3 Link Up - speed 10000 Mbps - full-duplex
    Done
	testpmd> create bonded device 1 1
    testpmd> add bonding slave 1 4
    testpmd> show port info 1
     ********************* Infos for port 1  *********************
    MAC address: 90:E2:BA:4A:54:81
    Connect to socket: 0
    memory allocation on the socket: 0
    Link status: up
    Link speed: 10000 Mbps
    Link duplex: full-duplex
    Promiscuous mode: enabled
    Allmulticast mode: disabled
    Maximum number of MAC addresses: 127
    Maximum number of MAC addresses of hash filtering: 4096
    VLAN offload:
       strip on
       filter on
       qinq(extend) off
    testpmd> show port info 4
     ********************* Infos for port 4  *********************
    MAC address: 90:E2:BA:4A:54:81
    Connect to socket: 1
    memory allocation on the socket: 0
    Link status: down
    Link speed: 10000 Mbps
    Link duplex: full-duplex
    Promiscuous mode: enabled
    Allmulticast mode: disabled
    Maximum number of MAC addresses: 1
    Maximum number of MAC addresses of hash filtering: 0
    VLAN offload:
      strip off
      filter off
      qinq(extend) off   

Continue with above case, add 2nd slave, check the configuration of a bonded device. Verify bonded device MAC address is that of primary slave and all slaves' MAC address is same. Below are the sample commands.

    testpmd> add bonding slave 2 4
    testpmd> show bonding config 4
    testpmd> show port info 1  ------(To check if port1,2,4 has the same MAC address as port1)
    testpmd> show port info 4
    testpmd> show port info 2

Set the bonded device's MAC address, and verify the bonded port and slaves' MAC address have changed to the new MAC address. 
    
    testpmd> set bonding mac_addr 4 00:11:22:00:33:44
    testpmd> show port info 1  ------(To check if port1,2,4 has the same MAC address as new MAC)
    testpmd> show port info 4
    testpmd> show port info 2

Change the primary slave to 2nd slave, verify that the bonded device's MAC and slave's MAC is still original. 
Remove 2nd slave from the bonded device, then verify 2nd slave device MAC address is returned to the correct MAC.

	testpmd> port start 4(Make sure the port4 has the primary slave)
    testpmd> show bonding config 4
    testpmd> set bonding primary 2 4
    testpmd> show bonding config 4-----(Verify that port2 is primary slave)
    testpmd> show port info 4
    testpmd> show port info 2
    testpmd> show port info 1-----(Verify that the bonding port and the slaves`s MAC is still original)
    testpmd> remove bonding slave 2 4
    testpmd> show bonding config 4-----(Verify that port1 is primary slave)
    testpmd> show port info 2  ------(To check if port2 returned to correct MAC)
    testpmd> show port info 4 ------(Verify that bonding device and slave MAC is still original when remove the primary slave)
    testpmd> show port info 1

Add another slave(3rd slave), then remove this slave from a bonded device, verify slave device MAC address is returned to the correct MAC.

    testpmd> add bonding slave 3 4
    testpmd> show bonding config 4
    testpmd> remove bonding slave 3 4
    testpmd> show bonding config 4
    testpmd> show port info 3  ------(To check if port3 has retuned to the correct MAC)


Test Case3: Basic bonding--Device Promiscuous Mode Test
========================================================

Use Setup#1.

Create bonded device, add 3 slaves. Set promiscuous mode on bonded eth dev. Verify all slaves of bonded device are changed to promiscuous mode. 


    ./app/testpmd -c f -n 4 -- -i
    .....
    Port 0 Link Up - speed 10000 Mbps - full-duplex
    Port 1 Link Up - speed 10000 Mbps - full-duplex
    Port 2 Link Up - speed 10000 Mbps - full-duplex
    Port 3 Link Up - speed 10000 Mbps - full-duplex
    Done
	testpmd> create bonded device 3 1
    testpmd> add bonding slave 0 4
    testpmd> add bonding slave 1 4
    testpmd> add bonding slave 2 4
    testpmd> show port info all---(Check if port0,1,2,4 has Promiscuous mode enabled)
     ********************* Infos for port 0  *********************
    MAC address: 90:E2:BA:4A:54:80
    Connect to socket: 0
    memory allocation on the socket: 0
    Link status: up
    Link speed: 10000 Mbps
    Link duplex: full-duplex
    **Promiscuous mode: enabled**
    Allmulticast mode: disabled
    Maximum number of MAC addresses: 127
    Maximum number of MAC addresses of hash filtering: 4096
    VLAN offload:
      strip on
      filter on
      qinq(extend) off

Send 1 packet to any bonded slave port(e.g: port0) with a different MAC destination than that of that eth dev(00:11:22:33:44:55) and verify that data is received at slave and bonded device. (port0 and port4).

    testpmd> set portlist 3,4
    testpmd> port start all
    testpmd> start
    testpmd> show port stats all----(Verify port0 has received 1 packet, port4 has received 1 packet, also port3 has transmitted 1 packet)

Disable promiscuous mode on bonded device.Verify all slaves of bonded eth dev have changed to be in non-promiscuous mode.This is applied to mode 0,2,3,4, for other mode, such as mode1, this is only applied to active slave.????
   
    testpmd> set promisc 4 off
    testpmd> show port info all---(Verify that port0,1,2 and 4 has promiscuous mode disabled, and it depends on the mode)

Send 1 packet to any bonded slave port(e.g: port0) with MAC not for that slave and verify that data is not received on bonded device and slave.
   
    testpmd> show port stats all----(Verify port0 has NOT received 1 packet, port4 NOT received 1 packet,too)

Send 1 packet to any bonded slave port(e.g: port0) with that slave's MAC and verify that data is received on bonded device and slave since the MAC address is correct.
   
    testpmd> show port stats all----(Verify port0 has received 1 packet, port4 received 1 packet,also port3 has transmitted 1 packet)

Test Case4: Mode 0(Round Robin) TX/RX test
==========================================

TX: 
Add ports 1-3 as slave devices to the bonded port 5.
Send a packet stream from port D on the traffic generator to be forwarded through the bonded port.
Verify that traffic is distributed equally in a round robin manner through ports 1-3 on the DUT back to the traffic generator.
The sum of the packets received on ports A-C should equal the total packets sent from port D.
The sum of the packets transmitted on ports 1-3 should equal the total packets transmitted from port 5 and received on port 4.

    ./app/testpmd -c f -n 4 -- -i
    ....

    testpmd> create bonded device 0 1
    testpmd> add bonding slave 0 4
    testpmd> add bonding slave 1 4
    testpmd> add bonding slave 2 4
    testpmd> set portlist 3,4
    testpmd> port start all
    testpmd> start
    testpmd> show port stats all----(Check port0,1,2,3 and 4 tx/rx packet stats)

Send 100 packets to port3 and verify port3 receive 100 packets, port4 transmit 100 packets,meanwhile the sum of the packets transmited on port 0-2 should equal the total packets transmitted from port4.
	
    testpmd> show port stats all----(Verify port3 100 rx packets,port0,1,2 have total 100 tx packets,port4 have 100 tx packets)

RX:
Add ports 1-3 as slave devices to the bonded port 5.
Send a packet stream from port A, B or C on the traffic generator to be forwarded through the bonded port 5 to port 4
Verify the sum of the packets transmitted from the traffic generator port is equal the total received packets on port 5 and transmitted on port 4.
Send a packet stream from the other 2 ports on the traffic generator connected to the bonded port slave ports. 
Verify data transmission/reception counts.

Send 10 pakcets from port 0-2 to port3.

    testpmd> clear port stats all
    testpmd> show port stats all----(Verify port0-2 have 10 rx packets respectively,port4 have 30 rx packets,meanwhile port3 have 30 tx packets)


Test Case5: Mode 0(Round Robin) Bring one slave link down 
========================================================= 

Add ports 1-3 as slave devices to the bonded port 5.
Bring the link on either port 1, 2 or 3 down.
Send a packet stream from port D on the traffic generator to be forwarded through the bonded port.
Verify that forwarded traffic is distributed equally in a round robin manner through the active bonded ports on the DUT back to the traffic generator.
The sum of the packets received on ports A-C should equal the total packets sent from port D.
The sum of the packets transmitted on the active bonded ports should equal the total packets transmitted from port 5 and received on port 4.
No traffic should be sent on the bonded port which was brought down.
Bring link back up link on bonded port. 
Verify that round robin return to operate across all bonded ports

Test Case6: Mode 0(Round Robin) Bring all slave links down 
========================================================== 

Add ports 1-3 as slave devices to the bonded port 5.
Bring the links down on all bonded ports.
Verify that bonded callback for link down is called.
Verify that no traffic is forwarded through bonded device

Test Case7: Mode 0(Round Robin) Performance test----TBD
=======================================================

Configure layer2 forwarding(testpmd) between bonded dev and a non bonded dev
Uni-directional flow: 
Use IXIA to generate traffic to non bonded eth dev
Verify that tx packet are evenly distrusted across active ports
Measure performance through bonded eth dev
Test with bonded port with 0, 1 and 2 slave ports.

Test Case8: Mode 1(Active Backup) TX/RX Test
============================================

Add ports 0-2 as slave devices to the bonded port 4.Set port 0 as active slave on bonded device. 

    testpmd> create bonded device 1 1
    testpmd> add bonding slave 0 4
    testpmd> add bonding slave 1 4
    testpmd> add bonding slave 2 4
    testpmd> show port info 4-----(Check the MAC address of bonded device)
    testpmd> set portlist 3,4
    testpmd> port start all
    testpmd> start

Send a packet stream(100 packets) from port A on the traffic generator to be forwarded through the bonded port4 to port3. Verify the sum of the packets transmitted from the traffic generator portA is equal the total received packets on port0, 4 and Port D and transmitted on port 4.

    testpmd> show port stats all---(Verify port0 receive 100 packets, and port4 receive 100 packets, and port3 transmit 100 packets)

Send a packet stream(100 packets) from portD on the traffic generator to be forwarded through port3 to the bonded port4. Verify the sum of the packets(100packets) transmitted from the traffic generator port is equal the total received packets on port4 and portA and transmitted on port4 and port0.
    
    testpmd> show port stats all---(Verify port0/port4 TX 100 packets, and port3 receive 100 packets)

Test Case9: Mode 1(Active Backup) Change active slave, RX/TX test
================================================================= 

Continuing from Test Case8.
Change the active slave port from port0 to port1.Verify that the bonded device's MAC has changed to slave1's MAC.

    testpmd> set bonding primary 1 4 

Repeat the transmission and reception(TX/RX) test verify that data is now transmitted and received through the new active slave and no longer through port0


Test Case10: Mode 1(Active Backup) Link up/down active eth dev
============================================================== 

Bring link between port A and port0 down. If tester is ixia, can use IxExplorer to set the "Simulate Cable Disconnect" at the port property.  
Verify that the active slave has been changed from port0. 
Repeat the transmission and reception test verify that data is now transmitted and received through the new active slave and no longer through port0

Test Case11: Mode 1(Active Backup) Bring all slave links down 
============================================================= 

Bring all slave ports of bonded port down.
Verify that bonded callback for link down is called and no active slaves. 
Verify that data cannot be sent or received through bonded port. Send 100 packets to port3 and verify that bonded port can't TX 100 packets.

Test Case12: Mode 1(Active Backup) Performance test---TBD
========================================================= 

Configure layer2 forwarding(testpmd) between bonded dev and a non bonded dev.Note: Make sure the core and the slave port are in the same socket.

Bi-directional flow: Use IXIA to generate traffic to non bonded eth dev(port3) and active port0, port1(non-active);Verify that tx packet are only sent to active port(port0) and bonded port4. Measure performance through slave port0 and port3's mapped IXIA ports' RX. Need check frame size 64,128,256,512,1024,1280,1518 related performance numbers. 

Try to check that if port0 is link down, port1 can be backup quickly and re-check the performance at port1 and port3's mapped IXIA ports' RX. 

    ./app/testpmd -c f -n 4 -- -i --burst=32 --rxfreet=32 --mbcache=250 --txpt=32 --rxht=8 --rxwt=0 --txfreet=32 --txrst=32 --txqflags=0xf01
    testpmd> create bonded device 1 0
    testpmd> add bonding slave 0 4
    testpmd> add bonding slave 1 4
    testpmd> add bonding slave 2 4
    testpmd> set portlist 3,4
    testpmd> port start all
    testpmd> start
    

Test Case13: Mode 2(Balance XOR) TX Load Balance test
===================================================== 

Bonded port will activate each slave eth dev based on the following hash function:

    ((dst_mac XOR src_mac) % (number of slave ports))

Send 300 packets from non-bonded port(port3),and verify these packets will be forwarded to bonded device. The bonded device will transimit these packets to all slaves.
Verify that each slave receive correct number of packets according to the policy. The total number of packets which are on slave should be equal as 300 packets. 


Test Case14: Mode 2(Balance XOR) TX Load Balance Link down
==========================================================

Bring link down of one slave.
Send 300 packets from non-bonded port(port3), and verify these packets will be forwarded to bonded device. 
Verify that each active slave receive correct number of packets(according to the mode policy), and the down slave will not receive packets.

Test Case15: Mode 2(Balance XOR) Bring all slave links down 
===========================================================

Bring all slave links down.
Verify that bonded callback for link down is called.
Verify no packet can be sent.

Test Case16: Mode 2(Balance XOR) Layer 3+4 forwarding
========================================================= 

Use “xmit_hash_policy()” to change to this forwarding mode
Create a stream of traffic which will exercise all slave ports using the transmit policy 

    ((SRC_PORT XOR DST_PORT) XOR ((SRC_IP XOR DST_IP) AND 0xffff) % # of Slaves

Transmit data through bonded device, verify TX packet count for each slave port is as expected

Test Case17: Mode 2(Balance XOR) RX test
========================================

Send 100 packets to each bonded slaves(port0,1,2)
Verify that each slave receives 100 packets and the bonded device receive a total 300 packets.
Verify that the bonded device forwards 300 packets to the non-bonded port(port4).



Test Case18: Mode 2(Balance XOR) Performance test--TBD
======================================================

Configure layer2 forwarding(testpmd) between bonded dev and a non bonded dev
Bi-directional flow: 
Use IXIA to generate traffic to non bonded eth dev and port0.
Verify that tx packet are distrusted according to XOR policy across active ports
Measure performance through bonded eth dev and these active ports mapped IXIA ports' RX.
Test with bonded port with 0, 1 and 2 slave ports.


Test Case19: Mode 3(Broadcast) TX/RX Test
=========================================

Add ports 0-2 as slave devices to the bonded port 4.Set port 0 as active slave on bonded device. 

    testpmd> create bonded device 3 1
    testpmd> add bonding slave 0 4
    testpmd> add bonding slave 1 4
    testpmd> add bonding slave 2 4
    testpmd> show port info 4-----(Check the MAC address of bonded device)
    testpmd> set portlist 3,4
    testpmd> port start all
    testpmd> start

RX: Send a packet stream(100 packets) from port A on the traffic generator to be forwarded through the bonded port4 to port3. Verify the sum of the packets transmitted from the traffic generator portA is equal the total received packets on port0, port4 and portD(Traffic generator).

    testpmd> show port stats all---(Verify port0 receive 100 packets, and port4 receive 100 packets, and port3 transmit 100 packets)

TX: Send a packet stream(100 packets) from portD on the traffic generator to be forwarded through port3 to the bonded port4. Verify the sum of the packets(100packets) transmitted from the traffic generator port is equal the total received packets on port4, portA and transmitted to port0.????
    
    testpmd> show port stats all---(Verify port3 RX 100 packets, and port0,1,2,4 TX 100 packets)

Test Case20: Mode 3(Broadcast) Bring one slave link down
========================================================

Bring one slave port link down. Send 100 packets through portD to port3, then port3 forwards to bondede device(port4), verify that the bonded device and other slaves TX the correct number of packets(100 packets for each port).


Test Case21: Mode 3(Broadcast) Bring all slave links down 
=========================================================

Bring all slave ports of bonded port down
Verify that bonded callback for link down is called
Verify that data cannot be sent or received through bonded port.

Test Case22: Mode 3(Broadcast) Performance test--TBD
====================================================

Configure layer2 forwarding(testpmd) between bonded dev and a non bonded dev
Bi-directional flow: 
Use IXIA to generate traffic to non bonded eth dev and port0.
Verify that tx packet are sent to all slave ports.
Measure performance through bonded eth dev and all slaves' mapped IXIA ports's RX.
Test with bonded port with slave ports 0,1,2. 
Can try to reduce slave numbers from 3 to 2 to check if performance has any difference.










