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
   "AS IS" AND ANY EXPR   ESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
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
IP fragmentation
==================
The IP fragmentation results are produced using ''ip_fragmentation'' application. 
The test application should run with both IPv4 and IPv6 fragmentation.

Prerequisites
=============

1. Hardware requirements:

- For each CPU socket, each memory channel should be populated with at least 1x DIMM
- Board is populated with at least 2x 1GbE or 10GbE ports. Special PCIe restrictions may
  be required for performance. For example, the following requirements should be
  met for Intel 82599 (Niantic) NICs:
  
	- NICs are plugged into PCIe Gen2 or Gen3 slots
	- For PCIe Gen2 slots, the number of lanes should be 8x or higher
	- A single port from each NIC should be used, so for 2x ports, 2x NICs should
	  be used

- NIC ports connected to traffic generator. It is assumed that the NIC ports
  P0, P1, P2, P3 (as identified by the DPDK application) are connected to the
  traffic generator ports TG0, TG1, TG2, TG3. The application-side port mask of
  NIC ports P0, P1, P2, P3 is noted as PORTMASK in this section.
  Traffic generator should support sending jumbo frames with size up to 9K.

2. BIOS requirements:

- Intel� Hyper-Threading Technology is ENABLED
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

5.Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

- The test can be run with IPv4 package. The LPM table used for IPv4 packet routing is: 

+-------+-------------------------------------+-----------+
|Entry #|LPM prefix (IP/length)               |Output port|
+-------+-------------------------------------+-----------+
|   0   |   100.10.0.0/16                     |     P2    |
+-------+-------------------------------------+-----------+
|   1   |   100.20.0.0/16                     |     P2    |
+-------+-------------------------------------+-----------+
|   2   |   100.30.0.0/16                     |     P0    |
+-------+-------------------------------------+-----------+
|   3   |   100.40.0.0/16                     |     P0    |
+-------+-------------------------------------+-----------+


- The test can be run with IPv6 package, which follows rules below.

 - There is no support for Hop-by-Hop or Routing extension headers in the packet 
   to be fragmented. All other optional headers, which are not part of the 
   unfragmentable part of the IPv6 packet are supported. 
   
 - When a fragment is generated, its identification field in the IPv6 
   fragmentation extension header is set to 0. This is not RFC compliant, but 
   proper identification number generation is out of the scope of the application 
   and routers in an IPv6 path are not allowed to fragment in the first place... 
   Generating that identification number is the job of a proper IP stack.
   
- The LPM table used for IPv6 packet routing is:   

+-------+-------------------------------------+-----------+
|Entry #|LPM prefix (IP/length)               |Output port|
+-------+-------------------------------------+-----------+
|   0   |   101:101:101:101:101:101:101:101/48|     P2    |
+-------+-------------------------------------+-----------+
|   1   |   201:101:101:101:101:101:101:101/48|     P2    |
+-------+-------------------------------------+-----------+
|   2   |   301:101:101:101:101:101:101:101/48|     P0    |
+-------+-------------------------------------+-----------+
|   3   |   401:101:101:101:101:101:101:101/48|     P0    |
+-------+-------------------------------------+-----------+

The following items are configured through the command line interface of the application:

  - The set of one or several RX queues to be enabled for each NIC port
  - The set of logical cores to execute the packet forwarding task
  - Mapping of the NIC RX queues to logical cores handling them.

Test Case 1: IP Fragmentation normal ip packet forward
==========================================================
With 1 input and 1 output port make sure that IP header and contents of the header are forwarded correctly for the frame sizes: 64, 128, 256, 512,1024, 1518 bytes.

Test Case 2: IP Fragmentation Don't fragment
==============================================
In TG set IP flag "Don't fragment" and make sure that frames with size 1519 bytes are discarded by ip_frag.

Test Case 3: IP Fragmentation May fragment
============================================
In TG set IP flag "May fragment" and send frames with the following sizes: 1519 bytes, 2K, 3K, 4K, 5K, 6K, 7K, 8K, 9K.
For each of them check that:
a.	Check number of output packets.
b.	Check header of each output packet: length, ID, fragment offset, flags.
c.	Check payload: size and contents as expected, not corrupted.



Test Case 4: Throughtput test
=============================

The test report should provide the throughput rate measurements (in mpps and % of the line rate for 2x NIC ports)
for the following input frame sizes: 64 bytes, 1518 bytes, 1519 bytes, 2K, 9k.

The following configurations should be tested:

|

+----------+-------------------------+----------------------+
|# of ports|  Socket/Core/HyperThread|Total # of sw threads |
+----------+-------------------------+----------------------+
|   2      |    1S/1C/1T             |          1           |
+----------+-------------------------+----------------------+
|   2      |    1S/1C/2T             |          2           |
+----------+-------------------------+----------------------+
|   2      |    1S/2C/1T             |          2           |
+----------+-------------------------+----------------------+
|   2      |    2S/1C/1T             |          2           |
+----------+-------------------------+----------------------+

|

Command line::

  ./ip_fragmentation -c <LCOREMASK> -n 4 -- [-P] -p PORTMASK
  -q <NUM_OF_PORTS_PER_THREAD>

