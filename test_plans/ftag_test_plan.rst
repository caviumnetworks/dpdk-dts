.. Copyright (c) <2016>, Intel Corporation
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

==========================
FM10k FTAG FORWARDING TEST
==========================

FM10000 supports the addition of a Fabric Tag (FTAG) to carry special
information between Switches, between Switch and PCIe Host Interface or
between Switch and Tunneling Engines. This tag is essential for a set of
switches to behave like one switch (switch aggregation). 

The FTAG is placed at the beginning of the frame.  The case will validate
packet forwarding function based on FTAG.

Prerequisites
-------------
Turn on CONFIG_RTE_LIBRTE_FM10K_FTAG_FWD in common_linuxapp configuration file.
Startup testpoint and export Port0 and Port1's GLORT ID.

Strip port logic value from mac table information.
There's the sample output from RubyRapid. From the output, port0's logic
value is 4122 and port1's logic value is 4123.

	<0>% show mac table all
	MAC                Mode      FID1 FID2 Type   Value  Trig ...
	------------------ --------- ---- ---- ------ ------ ----- 
	00:00:00:00:01:01  Dynamic   1    NA   Local  1      1     
	a0:36:9f:60:b6:6e  Static    1    NA   PF/VF  4506   1    
	a0:36:9f:60:b6:68  Static    1    NA   PF/VF  4123   1     
	00:00:00:00:01:00  Dynamic   1    NA   Local  1      1    
	a0:36:9f:60:b6:66  Static    1    NA   PF/VF  4122   1     


Strip port glort ID from stacking information.
There's the sample output from RubyRapid. Logic port0's GLORT ID is 0x4000.
Logic port1's GLORT ID is 0x4200.

	show stacking logical-port all
	<0>% show stacking logical-port all

	SW  GLORT  LOGICAL PORT   PORT TYPE
	---- ----- --------------- ---------
	...
	0 0x4000         4122    ?
	0 0x4200         4123    ?

Add port's GLORT ID into environment variables.
	export PORT1_GLORT=0x4200
	export PORT0_GLORT=0x4000
	
Test Case: Ftag forwarding unit test
====================================
1. port 0 pci 85:00.0, port 1 pci 87:00.0,start test application::

	./x86_64-native-linuxapp-gcc/app/test -c f -n 4 -w 0000:85:00.0,enable_ftag=1 -w 0000:87:00.0,enable_ftag=1

2. Run FTAG test function::

	RTE>>fm10k_ftag_autotest
	
3. Send one packet to Port0 and verify packet with ftag forwarded to Port1
	Receive 1 packets on port 0
	test for FTAG RX passed
	Send out 1 packets with FTAG on port 0
	Receive 1 packets on port 1
	test for FTAG TX passed
	Test OK

4. Send one packet to Port1 and verify packet with ftag forwarded to Port0
	Receive 1 packets on port 0
	test for FTAG RX passed
	Send out 1 packets with FTAG on port 0
	Receive 1 packets on port 1
	test for FTAG TX passed
	Test OK

