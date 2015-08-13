.. Copyright (c) <2010>, Intel Corporation
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
Mempool Autotests
=================

This is the test plan for the Intel® DPDK mempool library.

Description
===========

#. Basic tests: done on one core with and without cache:

   - Get one object, put one object
   - Get two objects, put two objects
   - Get all objects, test that their content is not modified and
     put them back in the pool.

#. Performance tests:

   Each core get *n_keep* objects per bulk of *n_get_bulk*. Then,
   objects are put back in the pool per bulk of *n_put_bulk*.

   This sequence is done during TIME_S seconds.

   This test is done on the following configurations:

   - Cores configuration (*cores*)

     - One core with cache
     - Two cores with cache
     - Max. cores with cache
     - One core without cache
     - Two cores without cache
     - Max. cores without cache

   - Bulk size (*n_get_bulk*, *n_put_bulk*)

     - Bulk get from 1 to 32
     - Bulk put from 1 to 32

   - Number of kept objects (*n_keep*)

     - 32
     - 128
