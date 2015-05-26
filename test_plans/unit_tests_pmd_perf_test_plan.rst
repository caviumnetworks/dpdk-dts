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

Prerequisites
=============
One 10Gb Ethernet port of the DUT is directly connected and link is up.

===========================
Continuous Mode Performance
===========================

This is the test plan for unit test to measure cycles/packet in NIC loopback
mode.

This section explains how to run the unit tests for pmd performance with 
continues stream control mode.
The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The final output of the test will be average cycles of IO used per packet.

======================
Burst Mode Performance
======================

This is the test plan for unit test to measure cycles/packet in NIC loopback
mode.

This section explains how to run the unit tests for pmd performance with 
burst stream control mode. For get accurate scalar fast performance, need 
disable INC_VECTOR in configuration file first.


The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The final output of the test will be matrix of average cycles of IO used per
packet.

        +--------+------+--------+--------+
        | Mode   | rxtx | rxonly | txonly |
        +========+======+========+========+
        | vector | 58   | 34     | 23     |
        +--------+------+--------+--------+
        | scalar | 89   | 51     | 38     |
        +--------+------+--------+--------+
        | full   | 73   | 31     | 42     |
        +--------+------+--------+--------+
        | hybrid | 59   | 35     | 23     |
        +--------+------+--------+--------+
