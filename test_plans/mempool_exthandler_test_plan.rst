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

========================
External mempool handler
========================

External Mempool Handler feature is an extension to the mempool API that
allows users to add and use an alternative mempool handler, which allows
external memory subsystems such as external hardware memory management
systems and software based memory allocators to be used with DPDK.

Test Case 1: Multiple producers and multiple consumers mempool handler
======================================================================
1. Change default mempool operation to "ring_mp_mc"
2. Run l2fwd and check packet forwarding normally with this mempool handler.

Test Case 2: Single producer and Single consumer mempool handler
================================================================
1. Change default mempool operation to "ring_sp_sc"
2. Run l2fwd and check packet forwarding normally with this mempool handler.

Test Case 3: Single producer and Multiple consumers mempool handler
===================================================================
1. Change default mempool operation to "ring_sp_mc"
2. Run l2fwd and check packet forwarding normally with this mempool handler.

Test Case 4: Multiple producers and single consumer mempool handler
===================================================================
1. Change default mempool operation to "ring_mp_sc"
2. Run l2fwd and check packet forwarding normally with this mempool handler.

Test Case 5: External stack mempool handler
===========================================
1. Change default mempool operation to "stack"
2. Run l2fwd and check packet forwarding normally with this mempool handler.


