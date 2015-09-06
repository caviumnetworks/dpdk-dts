.. Copyright (c) <2010,2011>, Intel Corporation
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

====================
Kernel NIC Interface
====================

Description
-----------

This document provides the plan for testing the Kernel NIC Interface 
application with support of rte_kni kernel module. 
Kernel NIC Interface is a DPDK alternative solution to the existing linux 
tun-tap interface for the exception path. Kernel NIC Interface allows the 
standard Linux net tools(ethtool/ifconfig/tcpdump) to facilitate managing the 
DPDK port. At the same time, it add an interface with the kernel net stack.
The test supports Multi-Thread KNI.

All kni model parameter deatil info on user guides:http://dpdk.org/doc/guides/sample_app_ug/kernel_nic_interface.html 

The ``rte_kni`` kernel module can be installed by a ``lo_mode`` parameter.

loopback disabled::

    insmod rte_kni.ko
    insmod rte_kni.ko "lo_mode=lo_mode_none"
    insmod rte_kni.ko "lo_mode=unsupported string"

loopback mode=lo_mode_ring enabled::

    insmod rte_kni.ko "lo_mode=lo_mode_ring"

loopback mode=lo_mode_ring_skb enabled::

    insmod rte_kni.ko "lo_mode=lo_mode_ring_skb"

The ``rte_kni`` kernel module can also be installed by a ``kthread_mode``
parameter. This parameter is ``single`` by default.

kthread single::

    insmod rte_kni.ko
    insmod rte_kni.ko "kthread_mode=single"
    
kthread multiple::

    insmod rte_kni.ko
    insmod rte_kni.ko "kthread_mode=multiple"

   
The ``kni`` application is run with EAL parameters and parameters for the 
application itself. For details about the EAL parameters, see the relevant 
DPDK **Getting Started Guide**. This application supports two parameters for 
itself.

    - ``--config="(port id, rx lcore, tx lcore, kthread lcore, kthread lcore, ...)"``: 
      Port and cores selection. Kernel threads are ignored if ``kthread_mode`` 
      is not ``multiple``.

ports cores::

    e.g.:
    
        --config="(0,1,2),(1,3,4)"              No kernel thread specified.
        --config="(0,1,2,21),(1,3,4,23)"        One kernel thread in use.
        --config="(0,1,2,21,22),(1,3,4,23,25)   Two kernel threads in use.

    - ``-P``: Promiscuous mode. This is off by default.

Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.


The DUT has at least 2 DPDK supported IXGBE NIC ports.

The DUT has to be able to install rte_kni kernel module and launch kni 
application with a default configuration (This configuration may change form a
system to another)::

    rmmod rte_kni
    rmmod igb_uio
    insmod ./x86_64-default-linuxapp-gcc/kmod/igb_uio.ko
    insmod ./x86_64-default-linuxapp-gcc/kmod/rte_kni.ko
    ./examples/kni/build/app/kni -c 0xa0001e -n 4 -- -P -p 0x3 --config="(0,1,2,21),(1,3,4,23)" &


Test Case: ifconfig testing
===========================

Launch the KNI application. Assume that ``port 2 and 3`` are used to this 
application. Cores 1 and 2 are used to read from NIC, cores 2 and 4 are used 
to write to NIC, threads 21 and 23 are used by the kernel.

As the kernel module is installed using ``"kthread_mode=single"`` the core 
affinity is set using ``taskset``::

    ./build/app/kni -c 0xa0001e -n 4 -- -P -p 0xc --config="(2,1,2,21),(3,3,4,23)"


Verify whether the interface has been added::

    ifconfig -a


If the application is launched successfully, it will add two interfaces in 
kernel net stack named ``vEth2_0``, ``vEth3_0``.

Interface name start with ``vEth`` followed by the port number and an 
additional incremental number depending on the number of kernel threads::

    vEth2_0: flags=4098<BROADCAST,MULTICAST>  mtu 1500
            ether 00:00:00:00:00:00  txqueuelen 1000  (Ethernet)
            RX packets 14  bytes 2098 (2.0 KiB)
            RX errors 0  dropped 10  overruns 0  frame 0
            TX packets 0  bytes 0 (0.0 B)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

    vEth3_0: flags=4098<BROADCAST,MULTICAST>  mtu 1500
            ether 00:00:00:00:00:00  txqueuelen 1000  (Ethernet)
            RX packets 13  bytes 1756 (1.7 KiB)
            RX errors 0  dropped 10  overruns 0  frame 0
            TX packets 0  bytes 0 (0.0 B)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0



Verify whether ifconfig can set Kernel NIC Interface up::

    ifconfig vEth2_0 up
    
Now ``vEth2_0`` is up and has IPv6 address::

    vEth2_0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
            inet6 fe80::92e2:baff:fe37:92f8  prefixlen 64  scopeid 0x20<link>
            ether 90:e2:ba:37:92:f8  txqueuelen 1000  (Ethernet)
            RX packets 30  bytes 4611 (4.5 KiB)
            RX errors 0  dropped 21  overruns 0  frame 0
            TX packets 6  bytes 468 (468.0 B)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0


Verify whether ifconfig can add an ipv6 address::
    
    ifconfig vEth2_0 add fe80::1

``vEth2_0`` has added ipv6 address::

    29: vEth2_0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qlen 1000
        inet6 fe80::1/128 scope link
           valid_lft forever preferred_lft forever
        inet6 fe80::92e2:baff:fe37:92f8/64 scope link
           valid_lft forever preferred_lft forever
           
           
Delete the IPv6 address::

    ifconfig vEth2_0 del fe80::1

The port deletes it::

    29: vEth2_0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qlen 1000
        inet6 fe80::92e2:baff:fe37:92f8/64 scope link
           valid_lft forever preferred_lft forever

Set MTU parameter::

    ifconfig vEth2_0 mtu 1300

``vEth2_0`` changes the mtu parameter::

    29: vEth2_0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1300 qdisc pfifo_fast state UNKNOWN mode DEFAULT qlen 1000
    link/ether 90:e2:ba:37:92:f8 brd ff:ff:ff:ff:ff:ff
    
Verify whether ifconfig can set ip address::

    ifconfig vEth2_0 192.168.2.1 netmask 255.255.255.192
    ip -family inet address show dev vEth2_0

``vEth2_0`` has IP address and netmask now::

    29: vEth2_0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1300 qdisc pfifo_fast state UNKNOWN qlen 1000
        inet 192.168.2.1/26 brd 192.168.2.63 scope global vEth2_0

Verify whether ifconfig can set ``vEth2_0`` down::

    ifconfig vEth2_0 down
    ifconfig vEth2_0

``vEth2_0`` is down and no ipv6 address::

    vEth2_0: flags=4098<BROADCAST,MULTICAST>  mtu 1300
            inet 192.168.2.1  netmask 255.255.255.192  broadcast 192.168.2.63
            ether 90:e2:ba:37:92:f8  txqueuelen 1000  (Ethernet)
            RX packets 70  bytes 12373 (12.0 KiB)
            RX errors 0  dropped 43  overruns 0  frame 0
            TX packets 25  bytes 4132 (4.0 KiB)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0


Repeat all the steps for interface ``vEth3_0``         
 
Test Case: Ping and Ping6 testing
=================================

If the application is launched successfully, it will add two interfaces in 
kernel net stack named ``vEth2_0``, ``vEth3_0``.

Assume the link status of ``vEth2_0`` is up and set ip address is ``192.168.2.1``
and ``vEth3_0`` is up and set ip address is ``192.168.3.1``. Verify the 
command ping::

    ping -w 1 -I vEth2_0 192.168.2.1

it can receive all packets and no packet loss::

    PING 192.168.2.1 (192.168.2.1) from 192.168.2.1 vEth2_0: 56(84) bytes of data.
    64 bytes from 192.168.2.1: icmp_req=1 ttl=64 time=0.040 ms

    --- 192.168.2.1 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 0.040/0.040/0.040/0.000 ms

Assume ``port A`` on tester is linked with ``port 2`` on DUT. Verify the 
command ping from tester::

    ping -w 1 -I "port A" 192.168.2.1

it can receive all packets and no packet loss.

Verify a wrong address::

    ping -w 1 -I vEth2_0 192.168.0.123

no packets is received::

    PING 192.168.0.123 (192.168.0.123) from 192.168.0.1 vEth2_0: 56(84) bytes of data.

    --- 192.168.0.123 ping statistics ---
    1 packets transmitted, 0 received, 100% packet loss, time 0ms

Verify the command ping6::

    ping6 -w 1 -I vEth2_0 "Eth2_0's ipv6 address"

it can receive all packets and no packet loss::

    PING fe80::92e2:baff:fe08:d6f0(fe80::92e2:baff:fe08:d6f0) from fe80::92e2:baff:fe08:d6f0 vEth2_0: 56 data bytes
    64 bytes from fe80::92e2:baff:fe08:d6f0: icmp_seq=1 ttl=64 time=0.070 ms

    --- fe80::92e2:baff:fe08:d6f0 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 0.070/0.070/0.070/0.000 ms

Verify the command ping6 from tester::

    ping6 -w 1 -I "port A" "Eth2_0's ipv6 address"

it can receive all packets and no packet loss.

Verify a wrong ipv6 address::

    ping6 -w 1 -I vEth2_0 "random ipv6 address"

no packets is received::

    PING fe80::92e2:baff:fe08:d6f1(fe80::92e2:baff:fe08:d6f1) from fe80::92e2:baff:fe08:d6f0 vEth2_0: 56 data bytes

    --- fe80::92e2:baff:fe08:d6f1 ping statistics ---
    1 packets transmitted, 0 received, 100% packet loss, time 0ms

Repeat all the steps for interface ``vEth3_0``
    
Test Case: Tcpdump testing
==========================

Assume ``port A and B`` on packet generator connects to NIC ``port 2 and 3``. 
Trigger the packet generator of bursting packets from ``port A and B`, then 
check if tcpdump can capture all packets. The packets should include 
``tcp`` packets, ``udp`` packets, ``icmp`` packets, ``ip`` packets, 
``ether+vlan tag+ip`` packets, ``ether`` packets.

Verify whether tcpdump can capture packets::

    tcpdump -i vEth2_0
    tcpdump -i vEth3_0


Test Case: Ethtool testing
==========================

In this time, KNI can only support ethtool commands which is to get information.
So all belowing commands are to show information commands.

Verify whether ethtool can show Kernel NIC Interface's standard information::

    ethtool vEth2_0

Verify whether ethtool can show Kernel NIC Interface's driver information::

    ethtool -i vEth2_0

Verify whether ethtool can show Kernel NIC Interface's statistics::

    ethtool -S vEth2_0

Verify whether ethtool can show Kernel NIC Interface's pause parameters::

    ethtool -a vEth2_0

Verify whether ethtool can show Kernel NIC Interface's offload parameters::

    ethtool -k vEth2_0

Verify whether ethtool can show Kernel NIC Interface's RX/TX ring parameters::

    ethtool -g vEth2_0

Verify whether ethtool can show Kernel NIC Interface's Coalesce parameters.
It is not currently supported::
      
    ethtool -c vEth2_0

Verify whether ethtool can show Kernel NIC Interface's MAC registers::
      
    ethtool -d vEth2_0

Verify whether ethtool can show Kernel NIC Interface's EEPROM dump::
      
    ethtool -e vEth2_0
    
Repeat all the steps for interface ``vEth3_0``

Test Case: Packets statistics testing
=====================================

Install the kernel module with loopback parameter ``lo_mode=lo_mode_ring_skb``
and launch the KNI application. 

Assume that ``port 2 and 3`` are used by this application::

    rmmod kni
    insmod ./kmod/rte_kni.ko "lo_mode=lo_mode_ring_skb"
    ./build/app/kni -c 0xff -n 3 -- -p 0xf -i 0xf -o 0xf0

Assume ``port A and B`` on tester connects to NIC ``port 2 and 3``.

Get the RX packets count and TX packets count::

    ifconfig vEth2_0

Send 5 packets from tester. And check whether both RX and TX packets of 
``vEth2_0`` have increased 5.

Repeat for interface ``vEth3_0``

Test Case: Stress testing
=========================

Insert the rte_kni kernel module 50 times while changing the parameters.
Iterate through lo_mode and kthread_mode values sequentially, include wrong
values. After each insertion check whether kni application can be launched 
successfully.

Insert the kernel module 50 times while changing randomly the parameters.
Iterate through lo_mode and kthread_mode values randomly, include wrong
values. After each insertion check whether kni application can be launched 
successfully::

        rmmod rte_kni
        insmod ./kmod/rte_kni.ko <Changing Parameters>
         ./build/app/kni -c 0xa0001e -n 4 -- -P -p 0xc --config="(2,1,2,21),(3,3,4,23)"


Using ``dmesg`` to check whether kernel module is loaded with the specified 
parameters. Some permutations, those with wrong values, must fail to 
success. For permutations with valid parameter values, verify the application can be
successfully launched and then close the application using CTRL+C.

Test Case: loopback mode performance testing
============================================

Compare performance results for loopback mode using:
  
    - lo_mode: lo_mode_fifo and lo_mode_fifo_skb.
    - kthread_mode: single and multiple.
    - Number of ports: 1 and 2.
    - Number of virtual interfaces per port: 1 and 2
    - Frame sizes: 64 and 256.
    - Cores combinations:
    
        - Different cores for Rx, Tx and Kernel.
        - Shared core between Rx and Kernel.
        - Shared cores between Rx and Tx.
        - Shared cores between Rx, Tx and Kernel.
        - Multiple cores for Kernel, implies multiple virtual interfaces per port.

::        

    insmod ./x86_64-default-linuxapp-gcc/kmod/igb_uio.ko
    insmod ./x86_64-default-linuxapp-gcc/kmod/rte_kni.ko <lo_mode and kthread_mode parameters>
    ./examples/kni/build/app/kni -c <Core mask> -n 4 -- -P -p <Port mask> --config="<Ports/Cores configuration>" &


At this point, the throughput is measured and recorded for the different 
frame sizes. After this, the application is closed using CTRL+C.

The measurements are presented in a table format.

+------------------+--------------+-------+-----------------+--------+--------+
| lo_mode          | kthread_mode | Ports | Config          | 64     | 256    |
+==================+==============+=======+=================+========+========+
|                  |              |       |                 |        |        |
+------------------+--------------+-------+-----------------+--------+--------+
        
        
Test Case: bridge mode performance testing
==========================================

Compare performance results for bridge mode using:
  
    - kthread_mode: single and multiple.
    - Number of ports: 2
    - Number of ports: 1 and 2.
    - Number of flows per port: 1 and 2
    - Number of virtual interfaces per port: 1 and 2
    - Frame size: 64.
    - Cores combinations:
    
        - Different cores for Rx, Tx and Kernel.
        - Shared core between Rx and Kernel.
        - Shared cores between Rx and Tx.
        - Shared cores between Rx, Tx and Kernel.
        - Multiple cores for Kernel, implies multiple virtual interfaces per port.

The application is launched and the bridge is setup using the commands below::

    insmod ./x86_64-default-linuxapp-gcc/kmod/rte_kni.ko <kthread_mode parameter>
    ./build/app/kni -c <Core mask> -n 4 -- -P -p <Port mask> --config="<Ports/Cores configuration>" &

    ifconfig vEth2_0 up
    ifconfig vEth3_0 up
    brctl addbr "br_kni"
    brctl addif br_kni vEth2_0
    brctl addif br_kni vEth3_0
    ifconfig br_kni up


At this point, the throughput is measured and recorded. After this, the
application is closed using CTRL+C and the bridge deleted::

    ifconfig br_kni down
    brctl delbr br_kni

    
The measurements are presented in a table format.   

+--------------+-------+-----------------------------+-------+
| kthread_mode | Flows | Config                      | 64    |
+==============+=======+=============================+=======+
|              |       |                             |       |
+--------------+-------+-----------------------------+-------+

Test Case: bridge mode without KNI performance testing
======================================================

Compare performance results for bridge mode using only Kernel bridge, no DPDK 
support. Use:

    - Number of ports: 2
    - Number of flows per port: 1 and 2
    - Frame size: 64.
    
Set up the interfaces and the bridge::

    rmmod rte_kni
    ifconfig vEth2_0 up
    ifconfig vEth3_0 up
    brctl addbr "br1"
    brctl addif br1 vEth2_0
    brctl addif br1 vEth3_0
    ifconfig br1 up

       
At this point, the throughput is measured and recorded. After this, the
application is closed using CTRL+C and the bridge deleted::

    ifconfig br1 down
    brctl delbr br1


The measurements are presented in a table format.   

+-------+-------+
| Flows | 64    |
+=======+=======+
| 1     |       |
+-------+-------+
| 2     |       |
+-------+-------+
    
Test Case: routing mode performance testing
===========================================

Compare performance results for routing mode using:
  
    - kthread_mode: single and multiple.
    - Number of ports: 2
    - Number of ports: 1 and 2.
    - Number of virtual interfaces per port: 1 and 2
    - Frame size: 64 and 256.
    - Cores combinations:
    
        - Different cores for Rx, Tx and Kernel.
        - Shared core between Rx and Kernel.
        - Shared cores between Rx and Tx.
        - Shared cores between Rx, Tx and Kernel.
        - Multiple cores for Kernel, implies multiple virtual interfaces per port.

The application is launched and the bridge is setup using the commands below::

    echo 1 > /proc/sys/net/ipv4/ip_forward

    insmod ./x86_64-default-linuxapp-gcc/kmod/rte_kni.ko <kthread_mode parameter>
    ./build/app/kni -c <Core mask> -n 4 -- -P -p <Port mask> --config="<Ports/Cores configuration>" &

    ifconfig vEth2_0 192.170.2.1
    ifconfig vEth2_0 192.170.3.1
    route add -net 192.170.2.0  netmask 255.255.255.0 gw 192.170.2.1
    route add -net 192.170.3.0  netmask 255.255.255.0 gw 192.170.3.1
    arp -s 192.170.2.2 vEth2_0
    arp -s 192.170.3.2 vEth3_0

At this point, the throughput is measured and recorded. After this, the
application is closed using CTRL+C.
    
The measurements are presented in a table format.   

+--------------+-------+-----------------------------+-------+-------+
| kthread_mode | Ports | Config                      | 64    | 256   |
+==============+=======+=============================+=======+=======+
|              |       |                             |       |       |
+--------------+-------+-----------------------------+-------+-------+


Test Case: routing mode without KNI performance testing
=======================================================

Compare performance results for routing mode using only Kernel, no DPDK 
support. Use:

    - Number of ports: 2
    - Frame size: 64 and 256
    
Set up the interfaces and the bridge::


    echo 1 > /proc/sys/net/ipv4/ip_forward
    rmmod rte_kni
    ifconfig vEth2_0 192.170.2.1
    ifconfig vEth2_0 192.170.3.1
    route add -net 192.170.2.0  netmask 255.255.255.0 gw 192.170.2.1
    route add -net 192.170.3.0  netmask 255.255.255.0 gw 192.170.3.1
    arp -s 192.170.2.2 vEth2_0
    arp -s 192.170.3.2 vEth3_0
       
At this point, the throughput is measured and recorded. After this, the
application is closed using CTRL+C.

The measurements are presented in a table format.

+-------+-------+-------+
| Ports | 64    | 256   |
+=======+=======+=======+
| 1     |       |       |
+-------+-------+-------+
| 2     |       |       |
+-------+-------+-------+
