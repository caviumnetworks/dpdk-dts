.. Copyright (c) 2016-2017 Intel Corporation
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

==============================================
Testing of Cryptodev Unit tests
==============================================


Description
===========

This document provides the plan for testing Cryptodev API via Cryptodev unit tests.
Unit tests include supported Hardware and Software PMD(polling mode device) and supported algorithms.
Cryptodev API provides ability to do encryption/decryption by integrating QAT(Intel@ QuickAssist
Technology) into DPDK. The QAT provides poll mode crypto driver support for 
Intel@ QuickAssist Adapter 8950 hardware accelerator.

The testing of Crytpodev API should be tested under either Intel QuickAssist Technology DH895xxC hardware
accelerator or AES-NI library.

This test suite will run all cryptodev related unit test cases. Alternatively, you could execute
the unit tests manually by app/test DPDK application.

Unit Test List
==============

- cryptodev_qat_autotest
- cryptodev_qat_perftest
- cryptodev_aesni_mb_perftest
- cryptodev_sw_snow3g_perftest
- cryptodev_qat_snow3g_perftest
- cryptodev_aesni_gcm_perftest
- cryptodev_openssl_perftest
- cryptodev_qat_continual_perftest
- cryptodev_aesni_mb_autotest
- cryptodev_openssl_autotest
- cryptodev_aesni_gcm_autotest
- cryptodev_null_autotest
- cryptodev_sw_snow3g_autotest
- cryptodev_sw_kasumi_autotest
- cryptodev_sw_zuc_autotest


Test Case Setup
===============

1. Build DPDK and app/test app
2. Bind cryptodev devices to igb_uio driver
3. Manually verify the app/test by this command, as example, in your build folder
* ./app/test -c 1 -n 1
* RTE>> cryptodev_qat_autotest

All Unit Test Cases are listed above. 

Expected all tests could pass in testing.

