.. Copyright (c) <2011>, Intel Corporation
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

==============================
Layer-3 Forwarding Exact Match
==============================

The Layer-3 Forwarding results are produced using ``l3fwd`` application. 

Prerequisites
=============

1. Hardware requirements:

    - For each CPU socket, each memory channel should be populated with at least 1x DIMM
    - Board is populated with 4x 1GbE or 10GbE ports. Special PCIe restrictions may
      be required for performance. For example, the following requirements should be
      met for Intel 82599 (Niantic) NICs:
      
    	- NICs are plugged into PCIe Gen2 or Gen3 slots
    	- For PCIe Gen2 slots, the number of lanes should be 8x or higher
    	- A single port from each NIC should be used, so for 4x ports, 4x NICs should
    	  be used
    
    - NIC ports connected to traffic generator. It is assumed that the NIC ports 
      P0, P1, P2, P3 (as identified by the DPDK application) are connected to the 
      traffic generator ports TG0, TG1, TG2, TG3. The application-side port mask of 
      NIC ports P0, P1, P2, P3 is noted as PORTMASK in this section.

2. BIOS requirements:

    - Intel Hyper-Threading Technology is ENABLED
    - Hardware Prefetcher is DISABLED
    - Adjacent Cache Line Prefetch is DISABLED
    - Direct Cache Access is DISABLED
  
3. Linux kernel requirements:

    - Linux kernel has the following features enabled: huge page support, UIO, HPET
    - Appropriate number of huge pages are reserved at kernel boot time
    - The IDs of the hardware threads (logical cores) per each CPU socket can be
      determined by parsing the file /proc/cpuinfo. The naming convention for the 
      logical cores is: C{x.y.z} = hyper-thread z of physical core y of CPU socket x, 
      with typical values of x = 0 .. 3, y = 0 .. 7, z = 0 .. 1. Logical cores 
      C{0.0.1} and C{0.0.1} should be avoided while executing the test, as they are
      used by the Linux kernel for running regular processes.

4. Software application requirements

5. Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.


- In hash mode, the hash table used for packet routing is:

|

+-------+-------------+-----------+-------------+-----------+-----------+--------+
| Entry | IPv4        | IPv4      | Port        | Port      | L4        | Output |
|   #   | destination | source    | destination | source    | protocol  | port   |
|       | address     | address   |             |           |           |        |
+-------+-------------+-----------+-------------+-----------+-----------+--------+
|   0   | 201.0.0.0   | 200.20.0.1|    102      |     12    |    TCP    |   P1   |
+-------+-------------+-----------+-------------+-----------+-----------+--------+
|   1   | 101.0.0.0   | 100.10.0.1|    101      |     11    |    TCP    |   P0   |
+-------+-------------+-----------+-------------+-----------+-----------+--------+
|   2   | 211.0.0.0   | 200.40.0.1|    102      |     12    |    TCP    |   P3   |
+-------+-------------+-----------+-------------+-----------+-----------+--------+
|   3   | 111.0.0.0   | 100.30.0.1|    101      |     11    |    TCP    |   P2   |
+-------+-------------+-----------+-------------+-----------+-----------+--------+


6. Traffic generator requirements

The flows need to be configured and started by the traffic generator:

|

+------+---------+----------+-----------+------+-------+--------+----------------------------------+
| Flow | Traffic | IPv4     | IPv4      | Port | Port  | L4     | IPv4                             |
|      | Gen.    | Dst.     | Src.      | Dst. | Src.  | Proto. | Dst Addr                         |
|      | Port    | Address  | Address   |      |       |        | Mask(Continuous Increment Host)  |
+------+---------+----------+-----------+------+-------+--------+----------------------------------+
|   1  |   TG0   | 201.0.0.0| 200.20.0.1|  102 |  12   |   TCP  |    255.240.0.0                   |
+------+---------+----------+-----------+------+-------+--------+----------------------------------+
|   2  |   TG1   | 101.0.0.0| 100.10.0.1|  101 |  11   |   TCP  |    255.240.0.0                   |
+------+---------+------------+---------+------+-------+--------+----------------------------------+



|

The queue column represents the expected NIC port RX queue where the packet 
should be written by the NIC hardware when RSS is enabled for that port.

Test Case: Layer-3 Forwarding (in Hash Mode)
============================================

The following items are configured through the command line interface of the 
application:

  - The set of one or several RX queues to be enabled for each NIC port
  - The set of logical cores to execute the packet forwarding task
  - Mapping of the NIC RX queues to logical cores handling them.
  - The set of hash-entry-num for the exact match
  
The test report should provide the throughput rate measurements (in mpps 
and % of the line rate for 4x NIC ports) as listed in the table below:

|

+----+---------+---------+-------------+---------+----------+------------------+
| #  |Number of|Total    |Number       |Total    |Number    | Throughput Rate  | 
|    |RX Queues|Number of|of Sockets/  |Number of|of NIX RX | Exact Match Mode |
|    |per NIC  |NIC RX   |Cores/Threads|Threads  |Queues per+------------------+
|    |Port     |Queues   |             |         |Thread    |  mpps  |    %    | 
+----+---------+---------+-------------+---------+----------+--------+---------+
| 1  |    1    |2        |1S/1C/1T     |1        |1         |        |         |        
+----+---------+---------+-------------+---------+----------+--------+---------+
| 2  |    1    |2        |1S/2C/1T     |2        |1         |        |         |                 
+----+---------+---------+-------------+---------+----------+--------+---------+
| 3  |    2    |4        |1S/4C/1T     |4        |2         |        |         |                
+----+---------+---------+-------------+---------+----------+--------+---------+


The application command line associated with each of the above tests is 
presented in the table below. The test report should present this table with
the actual command line used, replacing the PORTMASK and C{x.y.z} with their 
actual values used during test execution.

|

+-----+----------------------------------------------------------------------------------------------------------------------+
| #   | Command Line                                                                                                         |
+-----+----------------------------------------------------------------------------------------------------------------------+
|1    |./l3fwd -c coremask -n 3 -- -E -p 0x3 --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.0})'                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|2    |./l3fwd -c coremask -n 3 -- -E -p 0x3 --config '(P0,0,C{0.1.0}),(P1,0,C{0.2.0})'                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|3    |./l3fwd -c coremask -n 3 -- -E -p 0x3 --config '(P0,0,C{0.1.0}),(P0,1,C{0.2.0}),(P1,0,C{0.3.0}),(P1,1,C{0.4.0})'      |
+-----+----------------------------------------------------------------------------------------------------------------------+












































