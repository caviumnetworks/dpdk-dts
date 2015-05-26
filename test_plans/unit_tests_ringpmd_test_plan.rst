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

=================
Ring Pmd Autotest
=================

This is the test plan for the Intel® DPDK Ring poll mode driver feature.

This section explains how to run the unit tests for ring pmd. The test can be 
launched independently using the command line interface. 
This test is implemented as a linuxapp environment application and config 
RTE_LIBRTE_PMD_RING should be modified to 'Y'.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

Ring pmd unit test required two pair of virtual ethernet devices and one 
virtual ethernet devices with full rx&tx functions.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff --vdev='eth_ring0,nodeaction=:0:CREATE' 
     --vdev='eth_ring0,nodeaction=:0:ATTACH' --vdev='eth_ring1,nodeaction=:0:CREATE' 
     --vdev='eth ring2,nodeaction=:0:CREATE' --vdev='eth_ring2,nodeaction=:0:ATTACH'
  RTE>> ring_pmd_autotest

The final output of the test has to be "Test OK"
