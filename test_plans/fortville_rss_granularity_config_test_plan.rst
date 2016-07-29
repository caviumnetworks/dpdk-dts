.. Copyright (c) <2015>, Intel Corporation
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

==================================================================
Fortville - support granularity configuration of RSS, support 32-bit GRE keys
==================================================================

Description
===========
This document provides test plan for testing the function of Fortville:

1. Support granularity configuration of RSS

By default Fortville uses hash input set preloaded from NVM image which includes all fields 
- IPv4/v6+TCP/UDP port. Potential problem for this is global configuration per device and can 
affect all ports. It is required that hash input set can be configurable,  such as using IPv4
only or IPv6 only or IPv4/v6+TCP/UDP.

2. support 32-bit GRE keys

By default Fortville extracts only 24 bits of GRE key to FieldVector (NVGRE use case) but 
for Telco use cases full 32-bit GRE key is needed. It is required that both 24-bit and 32-bit
keys for GRE should be supported. the test plan is to test the API to switch between 24-bit and
32-bit keys 


Prerequisites
-------------

1. Hardware:
  1x Fortville_eagle NIC (4x 10G) 
  1x Fortville_spirit NIC (2x 40G)
  2x Fortville_spirit_single NIC (1x 40G)

2. software: 
  dpdk: http://dpdk.org/git/dpdk
  scapy: http://www.secdev.org/projects/scapy/


Test Case 1: test with flow type ipv4-tcp
===============================

1. config testpmd on DUT

1). set up testpmd with fortville NICs::
  ./testpmd -c 0x1ffff -n 4 -- -i --coremask=0x1fffe --portmask=0x3  --rxq=16 --txq=16 --txqflags=0

2). Reta Configuration(optional, if not set, will use default)::
  testpmd> port config 0 rss reta (hash_index,queue_id)

3). PMD fwd only receive the packets::
  testpmd> set fwd rxonly
  
4). rss recived package type configuration::
  testpmd> port config all rss tcp  

5). set hash function::  
  testpmd>set_hash_global_config 0 toeplitz ipv4-tcp enable

6). verbose configuration::
  testpmd> set verbose 8

7). start packet receive::
  testpmd> start
  
2. using scapy to send packets with ipv4-tcp on tester,
  
  sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/TCP(sport=1024,dport=1025)], iface="%s")
  
then got hash value and queue value that output from the testpmd on DUT. 

3. set hash input set to "none" by testpmd on dut,

testpmd> set_hash_input_set 0 ipv4-tcp none select

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
different from the values in step 2. 

4. set hash input set by testpmd on dut, enable src-ipv4 & dst-ipv4,

testpmd> set_hash_input_set 0 ipv4-tcp src-ipv4 add
testpmd> set_hash_input_set 0 ipv4-tcp dst-ipv4 add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
different from the values in step 2. 

5. set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4, tcp-src-port, tcp-dst-port

testpmd> set_hash_input_set 0 ipv4-tcp tcp-src-port add
testpmd> set_hash_input_set 0 ipv4-tcp tcp-dst-port add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values
should be different with the values from step 3 & step 4, should be same as step 2.

6. set hash input set by testpmd on dut, enable tcp-src-port, tcp-dst-port

testpmd> set_hash_input_set 0 ipv4-tcp none select
testpmd> set_hash_input_set 0 ipv4-tcp tcp-src-port add
testpmd> set_hash_input_set 0 ipv4-tcp tcp-dst-port add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
should be different with the values from step2 & step 3 & step 4 & step 5.

So it can be approved that with flow type ipv4-tcp, rss hash can be calculated by only included IPv4 fields
or only included TCP fields or both IPv4+TCP fields.


Test Case 2: test with flow type ipv4-udp
=========================================

1. config testpmd on DUT

1). set up testpmd with fortville NICs::
  ./testpmd -c 0x1ffff -n 4 -- -i --coremask=0x1fffe --portmask=0x3  --rxq=16 --txq=16 --txqflags=0

2). Reta Configuration(optional, if not set, will use default)::
  testpmd> port config 0 rss reta (hash_index,queue_id)

3). PMD fwd only receive the packets::
  testpmd> set fwd rxonly
  
4). rss recived package type configuration::
  testpmd> port config all rss udp  

5). set hash function::  
  testpmd>set_hash_global_config 0 toeplitz ipv4-udp enable

6). verbose configuration::
  testpmd> set verbose 8

7). start packet receive::
  testpmd> start
  
2. using scapy to send packets with ipv4-udp on tester::
  
  sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/UDP(sport=1024,dport=1025)], iface="%s"))
  
then got hash value and queue value that output from the testpmd on DUT. 

3. set hash input set to "none" by testpmd on dut, 

testpmd> set_hash_input_set 0 ipv4-udp none select

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
different from the values in step 2. 

4. set hash input set by testpmd on dut, enable src-ipv4 and dst-ipv4,

testpmd> set_hash_input_set 0 ipv4-udp src-ipv4 add
testpmd> set_hash_input_set 0 ipv4-udp dst-ipv4 add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
different from the values in step 2 & step 3. 

5. set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4, udp-src-port, udp-dst-port

testpmd> set_hash_input_set 0 ipv4-udp udp-src-port add
testpmd> set_hash_input_set 0 ipv4-udp udp-dst-port add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
should be different with the values from step 3 & step 4, should be same as step 2.

6. set hash input set by testpmd on dut, enable udp-src-port, udp-dst-port

testpmd> set_hash_input_set 0 ipv4-udp none select
testpmd> set_hash_input_set 0 ipv4-udp udp-src-port add
testpmd> set_hash_input_set 0 ipv4-udp udp-dst-port add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
should be different with the values from step2 & step 3 & step 4 & step 5.

So it can be approved that with flow type ipv4-udp, rss hash can be calculated by only included IPv4 fields
or only included UDP fields or both IPv4+UDP fields.

Test Case 3: test with flow type ipv6-tcp
=========================================

test mothed is same as Test Case 1, but it need change all ipv4 to ipv6,
and using scapy to send packets with ipv6-tcp on tester,

sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/TCP(sport=1024,dport=1025)], iface="%s")

and the test result should be same as Test Case 1.


Test Case 4: test with flow type ipv6-udp
=========================================

test mothed is same as Test Case 2, but it need change all ipv4 to ipv6,
and using scapy to send packets with ipv6-udp on tester,

sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/UDP(sport=1024,dport=1025)], iface="%s")

and the test result should be same as Test Case 2.

Test Case 5: test dual vlan(QinQ)
=====================================================
1. config testpmd on DUT

1). set up testpmd with fortville NICs::
 ./testpmd -c 0x1ffff -n 4 -- -i --coremask=0x1fffe --portmask=0x3  --rxq=16 --txq=16 --txqflags=0

2). set qinq on::
  testpmd> vlan set qinq on <port_id>
 
3). Reta Configuration(optional, if not set, will use default)::
  testpmd> port config 0 rss reta (hash_index,queue_id)

4). PMD fwd only receive the packets::
  testpmd> set fwd rxonly
  
5). verbose configuration::
  testpmd> set verbose 8

6). start packet receive::
  testpmd> start

7). rss recived package type configuration::
  testpmd> port config all rss ether    

2. using scapy to send packets with dual vlan (QinQ) on tester::
  
  sendp([Ether(dst="%s")/Dot1Q(id=0x8100,vlan=%s)/Dot1Q(id=0x8100,vlan=%s)], iface="%s")
 
then got hash value and queue value that output from the testpmd on DUT.

3. set hash input set to "none" by testpmd on dut::

testpmd> set_hash_input_set 0 l2_payload none select

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the value shoud be
same with the values in step 2. 

4. set hash input set by testpmd on dut, enable ovlan field::

testpmd> set_hash_input_set 0 l2_payload ovlan add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the value shoud be
different with the values in step 2.

5. set hash input set by testpmd on dut, enable ovlan, ivlan field::

testpmd> set_hash_input_set 0 l2_payload ivlan add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the value shoud be
different with the values in step 2.

Test Case 6: 32-bit GRE keys and 24-bit GRE keys test
=====================================================

1. config testpmd on DUT

1). set up testpmd with fortville NICs::
 ./testpmd -c 0x1ffff -n 4 -- -i --coremask=0x1fffe --portmask=0x3  --rxq=16 --txq=16 --txqflags=0

2). Reta Configuration(optional, if not set, will use default)::
  testpmd> port config 0 rss reta (hash_index,queue_id)

3). PMD fwd only receive the packets::
  testpmd> set fwd rxonly
  
4). rss recived package type configuration::
  testpmd> port config all rss all  

5). set hash function::  
  testpmd>set_hash_global_config 0 toeplitz ipv4-other enable

6). verbose configuration::
  testpmd> set verbose 8

7). start packet receive::
  testpmd> start

2. using scapy to send packets with GRE header on tester::
  
  sendp([Ether(dst="%s")/IP(src="192.168.0.1",dst="192.168.0.2",proto=47)/GRE(key_present=1,proto=2048,key=67108863)/IP()], iface="%s")
 
then got hash value and queue value that output from the testpmd on DUT.

3. set hash input set to "none" by testpmd on dut,

testpmd> set_hash_input_set 0 ipv4-other none select

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the value shoud be
different with the values in step 2. 

4. set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4

testpmd> set_hash_input_set 0 ipv4-other src-ipv4 add
testpmd> set_hash_input_set 0 ipv4-other dst-ipv4 add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the value shoud be
same with the values in step 2. 

4. set hash input set and gre-key-len=3 by testpmd on dut, enable gre-key

testpmd> global_config 0 gre-key-len 3
testpmd> set_hash_input_set 0 ipv4-other gre-key add

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
different with the values in step 2. 

5. set gre-key-len=4 by testpmd on dut, enable gre-key

testpmd> global_config 0 gre-key-len 4

send packet as step 2, got hash value and queue value that output from the testpmd on DUT, the values shoud be
different with the values in step 4. 

So with gre-key-len=3 (24bit gre key) or gre-key-len=4 (32bit gre key), different rss hash value and queue value
can be got, it can be proved that 32bit & 24bit gre key are supported by fortville.
