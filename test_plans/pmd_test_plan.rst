.. Copyright (c) <2010, 2011>, Intel Corporation
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

===
PMD
===

This document provides benchmark tests for the userland Intel®
82599 Gigabit Ethernet Controller (Niantic) Poll Mode Driver (PMD).
The userland PMD application runs the ``IO forwarding mode`` test
described in the PMD test plan document with different parameters for
the configuration of Niantic NIC ports.

The core configuration description is:

- 1C/1T: 1 Physical Core, 1 Logical Core per physical core (1 Hyperthread)
	using core #2 (socket 0, 2nd physical core)
- 1C/2T: 1 Physical Core, 2 Logical Cores per physical core (2 Hyperthreads)
	using core #2 and #14 (socket 0, 2nd physical core, 2 Hyperthreads)
- 2C/1T: 2 Physical Cores, 1 Logical Core per physical core
	using core #2 and #4 (socket 0, 2nd and 3rd physical cores)


Prerequisites
=============

Each of the 10Gb Ethernet* ports of the DUT is directly connected in
full-duplex to a different port of the peer traffic generator.

Using interactive commands, the traffic generator can be configured to
send and receive in parallel, on a given set of ports.

The tool ``vtbwrun`` (included in Intel® VTune™ Performance Analyzer)
will be used to monitor memory activities while running network
benchmarks to check the number of ``Memory Partial Writes`` and the
distribution of memory accesses among available Memory Channels.  This
will only be done on the userland application, as the tool requires a
Linux environment to be running in order to be used.

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Test Case: Packet Checking
==========================

The linuxapp is started with the following parameters:

::

  -c 0xffffff -n 3 -- -i --coremask=0x4 \
  --rxd=512 --txd=512 --burst=32 --txfreet=32 --rxfreet=64 --mbcache=128 --portmask=0xffff \
  --rxpt=4 --rxht=4 --rxwt=16 --txpt=36 --txht=0 --txwt=0 --txrst=32


The tester sends packets with different sizes (64, 65, 128, 256, 512, 1024,
1280 and 1518 bytes), using scapy, which will be forwarded by the DUT.
The test checks if the packets are correctly forwarded and if both RX and TX
packet sizes match.

Test Case: Descriptors Checking
===============================

The linuxapp is started with the following parameters:

::

  -c 0xffffff -n 3 -- -i --coremask=0x4 \
  --rxd={rxd} --txd={txd} --burst=32 --rxfreet=64 --mbcache=128 \
  --portmask=0xffff --txpt=36 --txht=0 --txwt=0 --txfreet=32 --txrst=32
  

IXIA sends packets with different sizes (64, 65, 128, 256, 512, 1024, 1280 and
1518 bytes) for diferent values of rxd and txd (between 128 and 4096)
The packets will be forwarded by the DUT. The test checks if the packets are
correctly forwarded.

Test Case: Performance Benchmarking
===================================

The linuxapp is started with the following parameters, for each of
the configurations referenced above:

1C/1T::

  -c 0xffffff -n 3 -- -i --coremask=0x4 \
  --rxd=512 --txd=512 --burst=32 --txfreet=32 --rxfreet=64 --mbcache=128 --portmask=0xffff \
  --rxpt=4 --rxht=4 --rxwt=16 --txpt=36 --txht=0 --txwt=0 --txrst=32

1C/2T::

  -c 0xffffff -n 3 -- -i --coremask=0x4004 \
  --rxd=512 --txd=512 --burst=32 --txfreet=32 --rxfreet=64 --mbcache=128 --portmask=0xffff \
  --rxpt=4 --rxht=4 --rxwt=16 --txpt=36 --txht=0 --txwt=0 --txrst=32

2C/1T::

  -c 0xffffff -n 3 -- -i --coremask=0x14 \
  --rxd=512 --txd=512 --burst=32 --txfreet=32 --rxfreet=64 --mbcache=128 --portmask=0xffff \
  --rxpt=4 --rxht=4 --rxwt=16 --txpt=36 --txht=0 --txwt=0 --txrst=32


The throughput is measured for each of these cases for the packet size
of 64, 65, 128, 256, 512, 1024, 1280 and 1518 bytes.
The results are printed in the following table:

+-------+---------+---------+---------+-----------+
| Frame |  1C/1T  |  1C/2T  |  2C/1   | wirespeed |
| Size  |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  64   |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  65   |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  128  |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  256  |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  512  |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  1024 |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  1280 |         |         |         |           |
+-------+---------+---------+---------+-----------+
|  1518 |         |         |         |           |
+-------+---------+---------+---------+-----------+


The memory partial writes are measured with the ``vtbwrun`` application and printed
in the following table:::


  Sampling Duration: 000000.00 micro-seconds
  ---       Logical Processor 0       ---||---       Logical Processor 1       ---
  ---------------------------------------||---------------------------------------
  ---   Intersocket QPI Utilization   ---||---   Intersocket QPI Utilization   ---
  ---------------------------------------||---------------------------------------
  ---      Reads (MB/s):         0.00 ---||---      Reads (MB/s):         0.00 ---
  ---      Writes(MB/s):         0.00 ---||---      Writes(MB/s):         0.00 ---
  ---------------------------------------||---------------------------------------
  ---  Memory Performance Monitoring  ---||---  Memory Performance Monitoring  ---
  ---------------------------------------||---------------------------------------
  --- Mem Ch 0: #Ptl Wr:      0000.00 ---||--- Mem Ch 0: #Ptl Wr:         0.00 ---
  --- Mem Ch 1: #Ptl Wr:      0000.00 ---||--- Mem Ch 1: Ptl Wr (MB/s):   0.00 ---
  --- Mem Ch 2: #Ptl Wr:      0000.00 ---||--- Mem Ch 2: #Ptl Wr:         0.00 ---
  --- ND0 Mem #Ptl Wr:        0000.00 ---||--- ND1 #Ptl Wr:               0.00 ---





