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

=========================
Dump log history Autotest
=========================

This is the test plan for dump history log of Intel® DPDK .

This section explains how to run the unit tests for dump history log. The test 
can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff
  RTE>> dump_log_history

The final output of the test will be the initial log of DPDK.

==================
Dump ring Autotest
==================

This is the test plan for dump the elements of Intel® DPDK ring.

This section explains how to run the unit tests for dump elements of ring. 
The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff
  RTE>> dump_ring

The final output of the test will be detail elements of DPDK ring.

=====================
Dump mempool Autotest
=====================

This is the test plan for dump the elements of Intel® DPDK mempool.

This section explains how to run the unit tests for dump elements of mempool.
The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff
  RTE>> dump_mempool

The final output of the test will be detail elements of DPDK mempool.

=============================
Dump Physical memory Autotest
=============================

This is the test plan for dump the elements of Intel® DPDK physical memory.

This section explains how to run the unit tests for dump elements of memory.
The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff
  RTE>> dump_physmem

The final output of the test will be detail elements of DPDK physical memory.

=====================
Dump Memzone Autotest
=====================

This is the test plan for dump the elements of Intel® DPDK memzone.

This section explains how to run the unit tests for dump elements of memzone.
The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff
  RTE>> dump_memzone

The final output of the test will be detail elements of DPDK memzone.

================
Dump Struct size
================

This is the test plan for dump the size of Intel® DPDK structure.

This section explains how to run the unit tests for dump structure size.
The test can be launched independently using the command line interface. 
This test is implemented as a linuxapp environment application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

The steps to run the unit test manually are as follow::
  
  # make -C ./app/test/
  # ./app/test/test -n 1 -c ffff
  RTE>> dump_struct_sizes

The final output of the test will be the size of DPDK structure.
