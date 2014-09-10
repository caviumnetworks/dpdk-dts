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

==================
Layer-3 Forwarding
==================

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

- In LPM mode, the LPM table used for packet routing is:

|

+-------+----------------------+-----------+
|Entry #|LPM prefix (IP/length)|Output port|
+-------+----------------------+-----------+
|   0   |    10.100.0.0/24     |     P1    |
+-------+----------------------+-----------+
|   1   |    10.101.0.0/24     |     P1    |
+-------+----------------------+-----------+
|   2   |    11.100.0.0/24     |     P2    |
+-------+----------------------+-----------+
|   3   |    11.101.0.0/24     |     P2    |
+-------+----------------------+-----------+
|   4   |    12.100.0.0/24     |     P3    |
+-------+----------------------+-----------+
|   5   |    12.101.0.0/24     |     P3    |
+-------+----------------------+-----------+
|   6   |    13.100.0.0/24     |     P4    |
+-------+----------------------+-----------+
|   7   |    13.101.0.0/24     |     P4    |
+-------+----------------------+-----------+

|

- In hash mode, the hash table used for packet routing is:

|

+-------+-------------+---------+-------------+-----------+-----------+--------+
| Entry | IPv4        | IPv4    | Port        | Port      | L4        | Output |
|   #   | destination | source  | destination | source    | protocol  | port   |
|       | address     | address |             |           |           |        |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   0   | 10.100.0.1  | 1.2.3.4 |     10      |     1     |    UDP    |   P1   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   1   | 10.101.0.1  | 1.2.3.4 |     10      |     1     |    UDP    |   P1   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   2   | 11.100.0.1  | 1.2.3.4 |     11      |     1     |    UDP    |   P2   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   3   | 11.101.0.1  | 1.2.3.4 |     11      |     1     |    UDP    |   P2   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   4   | 12.100.0.1  | 1.2.3.4 |     12      |     1     |    UDP    |   P3   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   5   | 12.101.0.1  | 1.2.3.4 |     12      |     1     |    UDP    |   P3   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   6   | 13.100.0.1  | 1.2.3.4 |     13      |     1     |    UDP    |   P0   |
+-------+-------------+---------+-------------+-----------+-----------+--------+
|   7   | 13.101.0.1  | 1.2.3.4 |     13      |     1     |    UDP    |   P0   |
+-------+-------------+---------+-------------+-----------+-----------+--------+

| 


5. Traffic generator requirements

The flows need to be configured and started by the traffic generator:

|

+------+---------+------------+---------+------+-------+--------+--------+
| Flow | Traffic | IPv4       | IPv4    | Port | Port  | L4     | NIC RX |
|      | Gen.    | Src.       | Dst.    | Src. | Dest. | Proto. | Queue  |
|      | Port    | Address    | Address |      |       |        | (RSS)  |
+------+---------+------------+---------+------+-------+--------+--------+
|   1  |   TG0   | 10.100.0.1 | 1.2.3.4 |  10  |   1   |   UDP  |    0   |
+------+---------+------------+---------+------+-------+--------+--------+
|   2  |   TG0   | 10.101.0.1 | 1.2.3.4 |  10  |   1   |   UDP  |    1   |
+------+---------+------------+---------+------+-------+--------+--------+
|   3  |   TG1   | 11.100.0.1 | 1.2.3.4 |  11  |   1   |   UDP  |    0   |
+------+---------+------------+---------+------+-------+--------+--------+
|   4  |   TG1   | 11.101.0.1 | 1.2.3.4 |  11  |   1   |   UDP  |    1   |
+------+---------+------------+---------+------+-------+--------+--------+
|   5  |   TG2   | 12.100.0.1 | 1.2.3.4 |  12  |   1   |   UDP  |    0   |
+------+---------+------------+---------+------+-------+--------+--------+
|   6  |   TG2   | 12.101.0.1 | 1.2.3.4 |  12  |   1   |   UDP  |    1   |
+------+---------+------------+---------+------+-------+--------+--------+
|   7  |   TG3   | 13.100.0.1 | 1.2.3.4 |  13  |   1   |   UDP  |    0   |
+------+---------+------------+---------+------+-------+--------+--------+
|   8  |   TG3   | 13.101.0.1 | 1.2.3.4 |  13  |   1   |   UDP  |    1   |
+------+---------+------------+---------+------+-------+--------+--------+

|

The queue column represents the expected NIC port RX queue where the packet 
should be written by the NIC hardware when RSS is enabled for that port.

Test Case: Layer-3 Forwarding (in Hash or LPM Mode)
===================================================

The following items are configured through the command line interface of the 
application:

  - The set of one or several RX queues to be enabled for each NIC port
  - The set of logical cores to execute the packet forwarding task
  - Mapping of the NIC RX queues to logical cores handling them.
  
The test report should provide the throughput rate measurements (in mpps 
and % of the line rate for 4x NIC ports) as listed in the table below:

|

+----+---------+---------+-------------+---------+----------+------------------+------------------+
| #  |Number of|Total    |Number       |Total    |Number    | Throughput Rate  | Throughput Rate  |
|    |RX Queues|Number of|of Sockets/  |Number of|of NIX RX | LPM Mode         | Hash Mode        |
|    |per NIC  |NIC RX   |Cores/Threads|Threads  |Queues per+------------------+------------------+
|    |Port     |Queues   |             |         |Thread    |  mpps  |    %    |  mpps  |    %    |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 1  |    1    |4        |1S/1C/1T     |1        |4         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 2  |    1    |4        |1S/1C/2T     |2        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 3  |    1    |4        |1S/2C/1T     |2        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 4  |    1    |4        |1S/2C/2T     |4        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 5  |    1    |4        |1S/4C/1T     |4        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 6  |    1    |4        |2S/1C/1T     |2        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 7  |    1    |4        |2S/1C/2T     |4        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 8  |    1    |4        |2S/2C/1T     |4        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
| 9  |    2    |8        |1S/1C/1T     |1        |8         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|10  |    2    |8        |1S/1C/2T     |2        |4         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|11  |    2    |8        |1S/2C/1T     |2        |4         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|12  |    2    |8        |1S/2C/2T     |4        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|13  |    2    |8        |1S/4C/1T     |4        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|14  |    2    |8        |1S/4C/2T     |8        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|15  |    2    |8        |2S/1C/1T     |2        |4         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|16  |    2    |8        |2S/1C/2T     |4        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|17  |    2    |8        |2S/2C/1T     |4        |2         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|18  |    2    |8        |2S/2C/2T     |8        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+
|19  |    2    |8        |2S/4C/1T     |8        |1         |        |         |        |         |
+----+---------+---------+-------------+---------+----------+--------+---------+--------+---------+

|

The application command line associated with each of the above tests is 
presented in the table below. The test report should present this table with
the actual command line used, replacing the PORTMASK and C{x.y.z} with their 
actual values used during test execution.

|

+-----+----------------------------------------------------------------------------------------------------------------------+
| #   | Command Line                                                                                                         |
+-----+----------------------------------------------------------------------------------------------------------------------+
|1    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.0}),(P2,0,C{0.1.0}),(P3,0,C{0.1.0})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|2    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.0}),(P2,0,C{0.1.1}),(P3,0,C{0.1.1})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|3    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.0}),(P2,0,C{0.2.0}),(P3,0,C{0.2.0})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|4    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.1}),(P2,0,C{0.2.0}),(P3,0,C{0.2.1})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|5    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.2.0}),(P2,0,C{0.3.0}),(P3,0,C{0.4.0})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|6    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.0}),(P2,0,C{1.1.0}),(P3,0,C{1.1.0})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|7    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.1.1}),(P2,0,C{1.1.0}),(P3,0,C{1.1.1})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|8    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P1,0,C{0.2.0}),(P2,0,C{1.1.0}),(P3,0,C{1.2.0})' |
+-----+----------------------------------------------------------------------------------------------------------------------+
|9    |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.1.0}),(P1,1,C{0.1.0}), |
|     |(P2,0,C{0.1.0}),(P2,1,C{0.1.0}),(P3,0,C{0.1.0}),(P3,1,C{0.1.0})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|10   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.1.0}),(P1,1,C{0.1.0}), |
|     |(P2,0,C{0.1.1}),(P2,1,C{0.1.1}),(P3,0,C{0.1.1}),(P3,1,C{0.1.1})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|11   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.1.0}),(P1,1,C{0.1.0}), |
|     |(P2,0,C{0.2.0}),(P2,1,C{0.2.0}),(P3,0,C{0.2.0}),(P3,1,C{0.2.0})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|12   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.1.1}),(P1,1,C{0.1.1}), |
|     |(P2,0,C{0.2.0}),(P2,1,C{0.2.0}),(P3,0,C{0.2.1}),(P3,1,C{0.2.1})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|13   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.2.0}),(P1,1,C{0.2.0}), |
|     |(P2,0,C{0.3.0}),(P2,1,C{0.3.0}),(P3,0,C{0.4.0}),(P3,1,C{0.4.0})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|14   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.1}),(P1,0,C{0.2.0}),(P1,1,C{0.2.1}), |
|     |(P2,0,C{0.3.0}),(P2,1,C{0.3.1}),(P3,0,C{0.4.0}),(P3,1,C{0.4.1})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|15   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.1.0}),(P1,1,C{0.1.0}), |
|     |(P2,0,C{1.1.0}),(P2,1,C{1.1.0}),(P3,0,C{1.1.0}),(P3,1,C{1.1.0})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|16   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.1.1}),(P1,1,C{0.1.1}), |
|     |(P2,0,C{1.1.0}),(P2,1,C{1.1.0}),(P3,0,C{1.1.1}),(P3,1,C{1.1.1})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|17   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.0}),(P1,0,C{0.2.0}),(P1,1,C{0.2.0}), |
|     |(P2,0,C{1.1.0}),(P2,1,C{1.1.0}),(P3,0,C{1.2.0}),(P3,1,C{1.2.0})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|18   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.1.1}),(P1,0,C{0.2.0}),(P1,1,C{0.2.1}), |
|     |(P2,0,C{1.1.0}),(P2,1,C{1.1.1}),(P3,0,C{1.2.0}),(P3,1,C{1.2.1})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+
|19   |./l3fwd -c 0xffffff -n 3 -- -P -p PORTMASK --config '(P0,0,C{0.1.0}),(P0,1,C{0.2.0}),(P1,0,C{0.3.0}),(P1,1,C{0.4.0}), |
|     |(P2,0,C{1.1.0}),(P2,1,C{1.2.0}),(P3,0,C{1.3.0}),(P3,1,C{1.4.0})'                                                      |
+-----+----------------------------------------------------------------------------------------------------------------------+

|

