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

==============
Mbuf Autotests
==============

This is the test plan for the Intel® DPDK mbuf library.

Description
===========

#. Allocate a mbuf pool.

   - The pool contains NB_MBUF elements, where each mbuf is MBUF_SIZE
     bytes long.

#. Test multiple allocations of mbufs from this pool.

   - Allocate NB_MBUF and store pointers in a table.
   - If an allocation fails, return an error.
   - Free all these mbufs.
   - Repeat the same test to check that mbufs were freed correctly.

#. Test data manipulation in pktmbuf.

   - Alloc an mbuf.
   - Append data using rte_pktmbuf_append().
   - Test for error in rte_pktmbuf_append() when len is too large.
   - Trim data at the end of mbuf using rte_pktmbuf_trim().
   - Test for error in rte_pktmbuf_trim() when len is too large.
   - Prepend a header using rte_pktmbuf_prepend().
   - Test for error in rte_pktmbuf_prepend() when len is too large.
   - Remove data at the beginning of mbuf using rte_pktmbuf_adj().
   - Test for error in rte_pktmbuf_adj() when len is too large.
   - Check that appended data is not corrupt.
   - Free the mbuf.
   - Between all these tests, check data_len and pkt_len, and
     that the mbuf is contiguous.
   - Repeat the test to check that allocation operations
     reinitialize the mbuf correctly.
