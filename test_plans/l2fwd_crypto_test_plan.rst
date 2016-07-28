.. Copyright (c) 2010,2011 Intel Corporation
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
Testing of CryptoDev in DPDK
==============================================


Description
===========

This document provides the plan for testing CryptoDev API. CryptoDev API 
provides the ability to do encryption/decryption by integrating QAT(Intel� QuickAssist 
Technology) into DPDK. The QAT provides poll mode crypto driver support for 
Intel� QuickAssist Adapter 8950 hardware accelerator.

The testing of CrytpoDev API should be tested under either Intel QuickAssist Technology DH895xxC hardware 
accelerator or AES-NI library.

AES-NI algorithm table 
The table below contains AES-NI Algorithms with CryptoDev API. 
Part of the algorithms are not supported currently.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| AES     | CBC               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| SHA     |                   |  SHA-1, SHA-224, SHA-384, SHA-256, SHA-512                                | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| HMAC    |                   |  Support SHA implementations SHA-1, SHA-224, SHA-256, SHA-384, SHA-512;   |
|         |                   |  Key Size versus Block size support: Key Size must be <= block size;      |
|         |                   |  Mac Len Supported SHA-1 10, 12, 16, 20 bytes;                            |
|         |                   |  Mac Len Supported SHA-256 16, 24, 32 bytes;                              |
|         |                   |  Mac Len Supported SHA-384 24,32, 40, 48 bytes;                           |
|         |                   |  Mac Len Supported SHA-512 32, 40, 48, 56, 64 bytes;                      |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

QAT algorithm table:
The table below contains Cryptographic Algorithm Validation with CryptoDev API. 
Part of the algorithms are not supported currently.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| AES     | CBC               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| SHA     |                   |  SHA-1, SHA-224, SHA-256, SHA-512                                         |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| HMAC    |                   |  Support SHA implementations SHA-1, SHA-224, SHA-256, SHA-512;            |
|         |                   |  Key Size versus Block size support: Key Size must be <= block size;      |
|         |                   |  Mac Len Supported SHA-1 10, 12, 16, 20 bytes;                            |
|         |                   |  Mac Len Supported SHA-224 14,16,20,24,28 bytes;                          |
|         |                   |  Mac Len Supported SHA-256 16, 24, 32 bytes;                              |
|         |                   |  Mac Len Supported SHA-384 24,32, 40, 48 bytes;                           |
|         |                   |  Mac Len Supported SHA-512 32, 40, 48, 56, 64 bytes;                      |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| GCM     |                   |  Key Sizes:128, 192, 256 bits;                                            |
|         |                   |  Associated Data Length: 0 ~ 240 bytes;                                   |
|         |                   |  Payload Length: 0 ~ (2^32 -1) bytes;                                     |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 96 bits;                                                     |
|         |                   |  Tag Lengths: 8, 12, 16 bytes;                                            |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| Snow3G  |  UEA2             |  Encrypt/Decrypt; Key size: 128                                           |
+         +---------+---------+---------+----------+----------+----------+----------+----------+----------+
|         |  UIA2             |  Encrypt/Decrypt; Key size: 128                                           |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

Limitations
=============
* Chained mbufs are not supported.
* Hash only is not supported.
* Cipher only is not supported (except Snow3g).
* Only in-place is currently supported (destination address is the same as source address).
* Only supports the session-oriented API implementation by QAT.  Support session-oriented and session-less APIs with AES-NI.
* Not performance tuned.

Prerequisites
=============
To test CryptoDev API, an example l2fwd-crypto is added into DPDK.

The test commands of l2fwd-crypto is below::
  * ./examples/l2fwd-crypto/build/app/l2fwd-crypto -n 4 -c COREMASK -- -p PORTMASK -q NQ --cdev (AESNI_MB|QAT) --chain (HASH_CIPHER|CIPHER_HASH) --cipher_algo (ALGO) --cipher_op (ENCRYPT|DECRYPT) --cipher_key (key_value) --iv (key_value) --auth_algo (ALGO) --auth_op (GENERATE|VERIFY) --auth_key (key_value) --sessionless

The operation of l2fwd-crypto are in 2 ways.
* For method CIPHER_HASH, the l2fwd-crypto will encrypt payload in packet first.
Then do authentification for the encrypted data. 
* For method HASH_CIPHER, the l2fwd-crypto will authenticate payload in packet first.
Then do encryption for the encrypted data. 

To do the function test, scapy can be used as traffic generator.
To do the performance test, traffic generator can be hardware equipment or 
software traffic generator.

The CryptoDev API supports Fedora or FreeBSD.

QAT/AES-NI installation 
==========================
If CryptoDev needs to use QAT to do encryption/decryption, QAT should be installed 
correctly. The steps how to install QAT is described in DPDK code directory 
dpdk/doc/guides/cryptodevs/qat.rst.

Once the driver is loaded, the software versions may be checked for each �dh89xxCC_devX� device as follows:
    more /proc/icp_dh895xcc_dev0/version

    +--------------------------------------------------+
    | Hardware and Software versions for device 0      |
    +--------------------------------------------------+
    |Hardware Version:             A0 SKU4             |
    |Firmware Version:             2.3.0               |
    |MMP Version:                  1.0.0               |
    |Driver Version:               2.3.0               |
    |Lowest Compatible Driver:     2.3                 |
    |QuickAssist API CY Version:   1.8                 |
    |QuickAssist API DC Version:   1.4                 |
    +--------------------------------------------------+

If CryptoDev needs to use AES-NI to do encryption/decryption, AES-NI library should be install 
correctly. The steps how to use AES-NI libary is described in DPDK code directory 
dpdk/doc/guides/cryptodevs/aesni_mb.rst.

Test case: Configuration test
====================================================
CryptoDev API supports different configuration.
This test tests different configuration with CrptoDev API.

Test case: CrytoDev Unit test
====================================================
The CrytoDev API has Unit test cases to support basic API level testing.

Compile Unit test
   cd isg_cid-dpdk_org/app/test
   make

Sub-case: AES-NI test case
------------------------------------------------------
run ./test -c 0xf -n 2 -- -i
>>cryptodev_aesni_autotest
  

Sub-case: QAT test case
------------------------------------------------------
run ./test -c 0xf -n 2 -- -i
>>cryptodev_qat_autotest

Test case: CryptoDev Function test
====================================================
For function test, the DUT forward UDP packets generated by scapy. 

After sending single packet from Scapy, Crytpodev function encrypt/decrypt the 
payload in packet by using algorithm setting in command. The l2fwd-crypto 
forward the packet back to tester. 
Use TCPDump to capture the received packet on tester. Then tester parses the payload 
and compare the payload with correct answer pre-stored in scripts.
+----------+                 +----------+
|          |                 |          |
|          | --------------> |          |
|  Tester  |                 |   DUT    |
|          |                 |          |
|          | <-------------> |          |
+----------+                 +----------+

Sub-case: AES-NI test case
------------------------------------------------------
Cryptodev AES-NI algorithm validation matrix is showed in table below.
+-------------+-------------+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  |  Auth_algo  |   Auth_op   |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  XCBC_MAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  MD5_HMAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         | AES_XCMC_MAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+

Sub-case: QAT AES test case
------------------------------------------------------
Cryptodev QAT AES algorithm validation matrix is showed in table below.

+-------------+-------------+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  |  Auth_algo  |   Auth_op   |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  XCBC_MAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  MD5_HMAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         | AES_XCMC_MAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+

Sub-case: QAT GCM test case
------------------------------------------------------
Cryptodev GCM algorithm validation matrix is showed in table below.
+-------------+-------------+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  |  Auth_algo  |   Auth_op   |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  XCBC_MAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  MD5_HMAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         | AES_XCMC_MAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+

Sub-case: AES-NI GCM test case
------------------------------------------------------
Cryptodev GCM algorithm validation matrix is showed in table below.
+-------------+-------------+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  |  Auth_algo  |   Auth_op   |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_GCM     | ENCRYPT     | 128         |  XCBC_MAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  MD5_HMAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         | AES_XCMC_MAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_GCM     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+


Sub-case: QAT Snow3G test case
------------------------------------------------------
Cryptodev Snow3G algorithm validation matrix is showed in table below.
Cipher only, hash-only and chaining functionality is supported for Snow3g.
+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  | 
+-------------+-------------+-------------+-------------+
|    CIPHER   | ECB         | ENCRYPT     | 128         | 
+-------------+-------------+-------------+-------------+


Test case: CryptoDev performance test
=======================================
For performance test, the DUT forward UDP packets generated by traffic generator. 
Also, queue and core number should be set into maximun number. 
+----------+                 +----------+
|          |                 |          |
|          | --------------> |          |
|   IXIA   |                 |   DUT    |
|          |                 |          |
|          | <-------------> |          |
+----------+                 +----------+

CryptoDev performance should be measured from different aspects ad below.
+-------+---------+---------+---------+----------+----------+ 
| Frame | 1S/1C/1T| 1S/1C/1T| 1S/2C/1T| 1S/2C/2T | 1S/2C/2T | 
| Size  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+  
|  64   |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  65   |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  128  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  256  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  512  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  1024 |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  1280 |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  1518 |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+

Sub-case: AES-NI test case
------------------------------------------------------
+-------------+-------------+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  |  Auth_algo  |   Auth_op   |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  MD5_HMAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+

Sub-case: QAT AES test case
------------------------------------------------------
+-------------+-------------+-------------+-------------+-------------+-------------+
|   Method    | Cipher_algo |  Cipher_op  | Cipyer_key  |  Auth_algo  |   Auth_op   |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| CIPHER_HASH | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  MD5_HMAC   | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 192         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 256         |  SHA1_HMAC  | GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA224_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA256_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA384_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
| HASH_CIPHER | AES_CBC     | ENCRYPT     | 128         |  SHA512_HMAC| GENERATE    |
+-------------+-------------+-------------+-------------+-------------+-------------+
