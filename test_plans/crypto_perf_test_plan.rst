.. Copyright (c) 2016,2017 Intel Corporation
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
Testing of Cryptodev performance in DPDK
==============================================


Description
===========

This document provides the test plan for testing Cryptodev performance by 
crypto perf application. The crypto perf application is a DPDK app under 
DPDK app folder. 

Crypto perf application supports most of Cryptodev PMDs(polling mode dirver)
Intel QuickAssist Technology DH895xxC/DH_C62xx hardware 
accelerator (QAT PMD), AESNI MB PMD, AESNI GCM PMD, NULL PMD, KASUMI PMD,
SNOW3G PMD,ZUC PMD or OPENSSL library PMD.

AESNI MB PMD algorithm table 
The table below contains AESNI MB algorithms which supported in crypto perf. 
Part of the algorithms are not supported currently.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | cbc               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | ctr               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| md      |                   |  md5                                                                      | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| sha     |                   |  sha1, sha2-224, sha2-384, sha2-256, sha2-512                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| hmac    |                   |  Support md5 and sha implementations sha1, sha2-224, sha2-256,            |
|         |                   |  sha2-384, sha2-512                                                       |
|         |                   |  Key Size versus Block size support: Key Size must be <= block size;      |
|         |                   |  Mac Len Supported sha1 10, 12, 16, 20 bytes;                             |
|         |                   |  Mac Len Supported sha2-256 16, 24, 32 bytes;                             |
|         |                   |  Mac Len Supported sha2-384 24,32, 40, 48 bytes;                          |
|         |                   |  Mac Len Supported sha2-512 32, 40, 48, 56, 64 bytes;                     |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

QAT algorithm table:
The table below contains QAT Algorithms which supported in crypto perf. 
Part of the algorithms are not supported currently.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | cbc               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | ctr               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| 3des    | cbc               |  Encrypt/Decrypt;Key size: 128, 192 bits                                  | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| 3des    | ctr               |  Encrypt/Decrypt;Key size: 128, 192 bits                                  | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| md      |                   |  md5                                                                      | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| sha     |                   |  sha1, sha2-224, sha2-256, sha2-384, sha2-512                             |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| hmac    |                   |  Support md5 and sha implementations sha1, sha2-224, sha2-256,            |
|         |                   |  sha2-384, sha2-512                                                       |
|         |                   |  Key Size versus Block size support: Key Size must be <= block size;      |
|         |                   |  Mac Len Supported sha1 10, 12, 16, 20 bytes;                             |
|         |                   |  Mac Len Supported sha2-256 16, 24, 32 bytes;                             |
|         |                   |  Mac Len Supported sha2-384 24,32, 40, 48 bytes;                          |
|         |                   |  Mac Len Supported sha2-512 32, 40, 48, 56, 64 bytes;                     |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     |  gcm              |  Key Sizes:128, 192, 256 bits;                                            |
|         |                   |  Associated Data Length: 0 ~ 240 bytes;                                   |
|         |                   |  Payload Length: 0 ~ (2^32 -1) bytes;                                     |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 96 bits;                                                     |
|         |                   |  Tag Lengths: 8, 12, 16 bytes;                                            |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| kasumi  |  f8               |  Encrypt/Decrypt; Key size: 128                                           |
+         +---------+---------+---------+----------+----------+----------+----------+----------+----------+
|         |  f9               |  Generate/Verify; Key size: 128                                           |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| snow3g  |  uea2             |  Encrypt/Decrypt; Key size: 128                                           |
+         +---------+---------+---------+----------+----------+----------+----------+----------+----------+
|         |  uia2             |  Generate/Verify; Key size: 128                                           |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

AESNI_GCM algorithm table 
The table below contains AESNI GCM PMD algorithms which are supported 
in crypto perf

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     |  gcm              |  Encrypt/Decrypt;Key Sizes:128, 256 bits;                                 |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 96 bits;                                                     |
|         |                   |  Generate/Verify;Key Sizes:128,192,256 bits;                              |
|         |                   |  Associated Data Length: 0 ~ 240 bytes;                                   |
|         |                   |  Payload Length: 0 ~ (2^32 -1) bytes;                                     |
|         |                   |  Tag Lengths: 8, 12, 16 bytes;                                            | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | gmac              |  Generate/Verify;Key Sizes:128,192,256 bits;                              | 
|         |                   |  Associated Data Length: 0 ~ 240 bytes;                                   |
|         |                   |  Payload Length: 0 ~ (2^32 -1) bytes;                                     |
|         |                   |  Tag Lengths: 8, 12, 16 bytes;                                            | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

NULL algorithm table 
The table below contains NULL algorithms which are supported in crypto perf. 
Part of the algorithms are not supported currently.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| null    |  null             |  Encrypt/Decrypt;Key Sizes:0 bits;                                        |
|         |                   |  IV Lengths: 0 bits;                                                      |
|         |                   |  Generate/Verify;Key Sizes:0 bits;                                        |
|         |                   |  Associated Data Length: 1 bytes;                                         |
|         |                   |  Payload Length: 0  bytes;                                                |
|         |                   |  Tag Lengths: 0 bytes;                                                    | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

KASUMI algorithm table 
The table below contains KASUMI algorithms which are supported in crypto perf.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| kasumi  |  f8               |  Encrypt/Decrypt;Key Sizes:128 bits;                                      |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 64 bits;                                                     |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| kasumi  |  f9               |  Generate/Verify;Key Sizes:128  bits;                                     | 
|         |                   |  Payload Length: 64 bytes;                                                |
|         |                   |  Tag Lengths: 4 bytes;                                                    | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

SNOW3G algorithm table 
The table below contains SNOW3G algorithms which are supported in crypto perf.

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| snow3g  |  uea2             |  Encrypt/Decrypt;Key Sizes:128 bits;                                      |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 128 bits;                                                    |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| snow3g  |  uia2             |  Generate/Verify;Key Sizes:128  bits;                                     | 
|         |                   |  Payload Length: 128 bytes;                                               |
|         |                   |  Tag Lengths: 4 bytes;                                                    | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

ZUC algorithm table 
The table below contains ZUC algorithms which are supported in crypto perf. 

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+   
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| zuc     |  eea3             |  Encrypt/Decrypt;Key Sizes:128 bits;                                      |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 128 bits;                                                    |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| zuc     |  eia2             |  Generate/Verify;Key Sizes:128  bits;                                     | 
|         |                   |  Payload Length: 128 bytes;                                               |
|         |                   |  Tag Lengths: 4 bytes;                                                    | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+

OPENSSL algorithm table:
The table below contains OPENSSL algorithms which are supported in crypto perf. 

+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
|Algorithm|  Mode             | Detail                                                                    | 
|         |                                                                                               |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | cbc               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | ctr               |  Encrypt/Decrypt;Key size: 128, 192, 256 bits                             | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| 3des    | cbc               |  Encrypt/Decrypt;Key size: 128, 192 bits                                  | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| 3des    | ctr               |  Encrypt/Decrypt;Key size: 128, 192 bits                                  | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| md      |                   |  md5                                                                      | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| sha     |                   |  sha1, sha2-224, sha2-256, sha2-384, sha2-512                             |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| hmac    |                   |  Support md5 and sha implementations sha1, sha2-224, sha2-256,            |
|         |                   |  sha2-384, sha2-512                                                       |
|         |                   |  Key Size versus Block size support: Key Size must be <= block size;      |
|         |                   |  Mac Len Supported sha1 10, 12, 16, 20 bytes;                             |
|         |                   |  Mac Len Supported sha2-256 16, 24, 32 bytes;                             |
|         |                   |  Mac Len Supported sha2-384 24,32, 40, 48 bytes;                          |
|         |                   |  Mac Len Supported sha2-512 32, 40, 48, 56, 64 bytes;                     |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     |  gcm              |  Encrypt/Decrypt;Key Sizes:128 bits;                                      |
|         |                   |  IV source: external;                                                     |
|         |                   |  IV Lengths: 96 bits;                                                     |
|         |                   |  Associated Data Length: 0 ~ 240 bytes;                                   |
|         |                   |  Generate/Verify; 128, 192,256 bytes;                                     |
|         |                   |  Payload Length: 64,128 bytes;                                            |
|         |                   |  Tag Lengths: 16 bytes;                                                   |
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+
| aes     | gmac              |  Generate/Verify;Key Sizes:128,192,256 bits;                              | 
|         |                   |  Associated Data Length: 0 ~ 240 bytes;                                   |
|         |                   |  Payload Length: 8 ~ (2^32 -4) bytes;                                     |
|         |                   |  Tag Lengths:16 bytes;                                                    | 
+---------+---------+---------+---------+----------+----------+----------+----------+----------+----------+


Prerequisites
=============
To test CryptoDev performance, an application 
test_crypto_perf is added into DPDK.

The test commands of test_crypto_perf is below::
    
    ./build/app/dpdk-test-crypto-perf -c COREMASK --vdev (AESNI_MB|QAT|AESNI_GCM|OPENSSL|SNOW3G|KASUMI|ZUC|NULL) -w (PCI:DEVICE:FUNCTION) -w (PCI:DEVICE:FUNCTION) -- --ptest (throughput|latency) --devtype (crypto_aesni_mb|crypto_qat|crypto_aes_gcm|crypto_openssl|crypto_snow3g|crypto_kasumi|crypto_zuc|crypto_null) --optype (aead|cipher-only|auth-only|cipher-then-auth|auth-then-cipher)  --cipher-algo (ALGO) --cipher-op (encrypt|decrypt) --cipher-key-sz (key_size) --cipher-iv-sz (iv_size) --auth-algo (ALGO) --auth-op (generate|verify) --auth-key-sz (key_size) --auth-aad-sz (aad_size) --auth-digest-sz (digest_size) --total-ops (ops_number) --burst-sz (burst_size) --buffer-sz (buffer_size) 



Test case: CryptoDev performance test
====================================================
+----------+                 +----------+
|          |                 |          |
|          | --------------> |          |
|  Tester  |                 |   DUT    |
|          |                 |          |
|          | <-------------> |          |
+----------+                 +----------+

common::
        
 --vdev (AESNI_MB|QAT|AESNI_GCM|OPENSSL|SNOW3G|KASUMI|ZUC|NULL) this value can be set as : crypto_aesni_mb_pmd, crypto_aes_gcm_pmd, crypto_openssl_pmd, crypto_snow3g_pmd, crypto_kasumi_pmd, crypto_zuc_pmd or  crypto_null_pmd . if pmd is QAT this parameter should not be set

 -w (PCI:DEVICE:FUNCTION) this value is the port whitelist or QAT device whitelist . if vdev is  set and devtype is not crypto_qat , the QAT device whitelist is not needed , but you also can set it on the cmd line . 
 
 --optype (aead|cipher-only|auth-only|cipher-then-auth|auth-then-cipher): if cipher-algo is aes-gcm or gmac this value must be set to aead . otherwise it will  be set to others. please notice , null algorithm only support cipher-only test.

 other parameters please reference above table's parameter .

QAT PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_qat --optype cipher-then-auth  --cipher-algo aes-cbc --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 16 --auth-algo sha1-hmac --auth-op generate --auth-key-sz 64 --auth-aad-sz 0 --auth-digest-sz 20 --total-ops 10000000 --burst-sz 32 --buffer-sz 1024

AESNI_MB PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_aesni_mb_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_aesni_mb --optype cipher-then-auth  --cipher-algo aes-cbc --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 16 --auth-algo sha1-hmac --auth-op generate --auth-key-sz 64 --auth-aad-sz 0 --auth-digest-sz 20 --total-ops 10000000 --burst-sz 32 --buffer-sz 1024         

AESNI_GCM PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_aesni_gcm_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_aesni_gcm  --optype aead  --cipher-algo aes-gcm --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 12 --auth-algo aes-gcm --auth-op generate --auth-key-sz 16 --auth-aad-sz 4 --auth-digest-sz 12 --total-ops 10000000 --burst-sz 32 --buffer-sz 1024

OPENSSL PMD Commmand line Eg:: 

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_openssl_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_openssl --optype cipher-then-auth  --cipher-algo aes-cbc --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 16 --auth-algo sha1-hmac --auth-op generate --auth-key-sz 64 --auth-aad-sz 0 --auth-digest-sz 20 --total-ops 10000000 --burst-sz 32 --buffer-sz 64

NULL PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_null_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_null  --optype cipher-only  --cipher-algo null --cipher-op encrypt --cipher-key-sz 0 --cipher-iv-sz 0  --total-ops 10000000 --burst-sz 32 --buffer-sz 1024

KASUMI PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_kasumi_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_kasumi --optype cipher-then-auth  --cipher-algo kasumi-f8 --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 8 --auth-algo kasumi-f9 --auth-op generate --auth-key-sz 16 --auth-aad-sz 8 --auth-digest-sz 4 --total-ops 10000000 --burst-sz 32 --buffer-sz 1024

SNOW3G PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_snow3g_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_snow3g --optype cipher-then-auth  --cipher-algo snow3g-uea2 --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 16 --auth-algo snow3g-uia2 --auth-op generate --auth-key-sz 16 --auth-aad-sz 16 --auth-digest-sz 4 --total-ops 10000000 --burst-sz 32 --buffer-sz 1024

ZUC PMD Commmand line Eg::

    ./build/app/dpdk-test-crypto-perf -c 0xf --vdev crypto_zuc_pmd  -w 0000:01:00.0 -w 0000:03:3d.0 -- --ptest throughput --devtype crypto_zuc_mb --optype cipher-then-auth  --cipher-algo zuc-eea3 --cipher-op encrypt --cipher-key-sz 16 --cipher-iv-sz 16 --auth-algo zuc-eia3  --auth-op generate --auth-key-sz 16 --auth-aad-sz 16 --auth-digest-sz 4 --total-ops 10000000 --burst-sz 32 --buffer-sz 1024


