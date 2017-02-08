.. Copyright (c) <2017>, Intel Corporation
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

========================
External mempool handler
========================
   
External Mempool Handler feature is an extension to the mempool API that
allows users to add and use an alternative mempool handler, which allows
external memory subsystems such as external hardware memory management
systems and software based memory allocators to be used with DPDK.

Test Case 1: Multiple producers and multiple consumers
======================================================
1. Change default mempool handler operations to "ring_mp_mc"
2. Start test app and verify mempool autotest passed

   test -n 4 -c f
   RTE>> mempool_autotest

3. Start testpmd with two ports and start forwarding

   testpmd -c 0x6 -n 4  -- -i --portmask=0x3 --txqflags=0
   testpmd> set fwd mac
   testpmd> start
   
4. Send hundreds of packets from tester ports
5. verify forwarded packets sequence and integrity

Test Case 2: Single producer and Single consumer
================================================
1. Change default mempool operation to "ring_sp_sc"
2. Start test app and verify mempool autotest passed

   test -n 4 -c f
   RTE>> mempool_autotest

3. Start testpmd with two ports and start forwarding

   testpmd -c 0x6 -n 4  -- -i --portmask=0x3 --txqflags=0
   testpmd> set fwd mac
   testpmd> start
   
4. Send hundreds of packets from tester ports
5. verify forwarded packets sequence and integrity

Test Case 3: Single producer and Multiple consumers
===================================================
1. Change default mempool operation to "ring_sp_mc"
2. Start test app and verify mempool autotest passed

   test -n 4 -c f
   RTE>> mempool_autotest

3. Start testpmd with two ports and start forwarding

   testpmd -c 0x6 -n 4  -- -i --portmask=0x3 --txqflags=0
   testpmd> set fwd mac
   testpmd> start
   
4. Send hundreds of packets from tester ports
5. verify forwarded packets sequence and integrity

Test Case 4: Multiple producers and single consumer
===================================================
1. Change default mempool operation to "ring_mp_sc"
2. Start test app and verify mempool autotest passed

   test -n 4 -c f
   RTE>> mempool_autotest

3. Start testpmd with two ports and start forwarding

   testpmd -c 0x6 -n 4  -- -i --portmask=0x3 --txqflags=0
   testpmd> set fwd mac
   testpmd> start
   
4. Send hundreds of packets from tester ports
5. verify forwarded packets sequence and integrity
   
Test Case 4: Stack mempool handler
==================================
1. Change default mempool operation to "stack"
2. Start test app and verify mempool autotest passed

   test -n 4 -c f
   RTE>> mempool_autotest

3. Start testpmd with two ports and start forwarding

   testpmd -c 0x6 -n 4  -- -i --portmask=0x3 --txqflags=0
   testpmd> set fwd mac
   testpmd> start
   
4. Send hundreds of packets from tester ports
5. verify forwarded packets sequence and integrity
