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

================================
Linux User Space Stability Tests
================================
This is the test report for the Intel® DPDK Linux user space stability tests
described in the test plan document.

Test Case: Stress test
======================
Run under heavy traffic for a long time. At the end of the test period, check
that the traffic is still flowing and there is no drop in the throughput rate.

Recommended test configuration: testpmd application using a single logical core
to handle line rate traffic from two 10GbE ports. Recommended test duration: 
24 hours.

Test Case: Repetitive system restart
====================================
Check that the system is still working after the application is shut down and 
restarted repeatedly under heavy traffic load. After the last test iteration, 
the traffic should still be flowing through the system with no drop in the 
throughput rate.

Recommended test configuration: testpmd application using a single logical core
to handle line rate traffic from two 10GbE ports.

Test Case: Packet integrity test
================================
Capture output packets selectively and check that the packet headers are as 
expected, with the payload not corrupted or truncated.

Recommended test configuration: testpmd application using a single logical core
to handle line rate traffic from two 10GbE ports.

Test Case: Cable removal test
=============================
Check that the traffic stops when the cable is removed and resumes with no drop 
in the throughput rate after the cable is reinserted.

Test Case: Mix of different NIC types
=====================================
Check that a mix of different NIC types is supported. The system should 
recognize all the NICs that are part of the system and are supported by the 
Intel DPDK PMD. Check that ports from NICs of different type can send and 
receive traffic at the same time.

Recommended test configuration: testpmd application using a single logical core
to handle line rate traffic from two 1GbE ports (e.g. Intel 82576 NIC) and 
two 10GbE ports (e.g. Intel 82599 NIC).

Test Case: Coexistence of kernel space drivers with Poll Mode Drivers
=====================================================================
Verify that Intel DPDK PMD running in user space can work with the kernel 
space space NIC drivers.

Recommended test configuration: testpmd application using a single logical core
to handle line rate traffic from two 1GbE ports (e.g. Intel 82576 NIC) and 
two 10GbE ports (e.g. Intel 82599 NIC). Kernel space driver for Intel 82576 NIC 
used for management.


