# BSD LICENSE
#
# Copyright(c) 2016-2017 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hmac
import hashlib
import binascii
import time
import os
import sys
import utils
import commands
from test_case import TestCase
from packet import Packet, sniff_packets, load_sniff_packets, save_packets

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Manually Install the CryptoMobile Python Library,
# Before running this test suite
# Web link : https://github.com/mitshell/CryptoMobile
import CryptoMobile.CM as cm


class TestL2fwdCrypto(TestCase):

    def set_up_all(self):

        self.core_config = "1S/2C/1T"
        self.number_of_ports = 1
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= self.number_of_ports,
                    "Not enough ports for " + self.nic)
        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.logger.info("core config = " + self.core_config)
        self.logger.info("number of ports = " + str(self.number_of_ports))
        self.logger.info("dut ports = " + str(self.dut_ports))
        self.logger.info("ports_socket = " + str(self.ports_socket))

        self.core_mask = utils.create_mask(self.dut.get_core_list(
                                         self.core_config,
                                         socket=self.ports_socket))
        self.port_mask = utils.create_mask([self.dut_ports[0]])

        self.tx_port = self.tester.get_local_port(self.dut_ports[0])
        self.rx_port = self.tester.get_local_port(self.dut_ports[0])

        self.tx_interface = self.tester.get_interface(self.tx_port)
        self.rx_interface = self.tester.get_interface(self.rx_port)

        self.logger.info("core mask = " + self.core_mask)
        self.logger.info("port mask = " + self.port_mask)
        self.logger.info("tx interface = " + self.tx_interface)
        self.logger.info("rx interface = " + self.rx_interface)

        # Rebuild the dpdk with cryptodev pmds
        self.dut.send_expect("export AESNI_MULTI_BUFFER_LIB_PATH=/root/ipsec_043/code/", "#")
        self.dut.send_expect("export LIBSSO_SNOW3G_PATH=/root/libsso_snow3g/snow3g/", "#")
        self.dut.send_expect("export LIBSSO_ZUC_PATH=/root/libsso_zuc.1.0.1.1-8/zuc", "#")
        self.dut.send_expect("export LIBSSO_KASUMI_PATH=/root/LibSSO_0_3_1/isg_cid-wireless_libs/ciphers/kasumi/", "#")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=n$/CONFIG_RTE_LIBRTE_PMD_QAT=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=n$/CONFIG_RTE_LIBRTE_PMD_KASUMI=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_OPENSSL=n$/CONFIG_RTE_LIBRTE_PMD_OPENSSL=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=n$/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=y/' config/common_base", "# ") 
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_ZUC=n$/CONFIG_RTE_LIBRTE_PMD_ZUC=y/' config/common_base", "# ")
        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.dut.target)
        
        # l2fwd-crypto compile
        out = self.dut.build_dpdk_apps("./examples/l2fwd-crypto")
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")
        
        # Bind QAT VF devices
        out = self.dut.send_expect("lspci -d:443|awk '{print $1}'", "# ", 10)
        self.dut.send_expect('echo "8086 0443" > /sys/bus/pci/drivers/igb_uio/new_id', "# ", 10)
        for line in out.replace("\r", "\n").replace("\n\n", "\n").split("\n"):
            cmd = "echo 0000:{} > /sys/bus/pci/devices/0000\:{}/driver/unbind".format(line, line.replace(":", "\:"))
            self.dut.send_expect(cmd, "# ", 10)
            cmd = "echo 0000:{} > /sys/bus/pci/drivers/igb_uio/bind".format(line)
            self.dut.send_expect(cmd, "# ", 10)

    def set_up(self):
        pass

    def test_qat_AES_CBC_auto(self):
        result = True
        self.logger.info("Test qat_c_AES_CBC_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_AES_CBC_00"):
            result = False
        
    def test_qat_AES_CTR_auto(self):
        result = True
        self.logger.info("Test qat_c_AES_CTR_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_AES_CTR_00"):
            result = False
        
    def test_qat_AES_GCM_auto(self):
        result = True
        self.logger.info("Test qat_c_AES_GCM_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_AES_GCM_00"):
            result = False
    
    def test_qat_h_MD_SHA_auto(self):
        result = True
        self.logger.info("Test qat_h_MD_SHA_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_MD_SHA_00"):
            result = False
    
    def test_qat_h_AES_XCBC_MAC_auto(self):
        result = True
        self.logger.info("Test qat_h_AES_XCBC_MAC_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_AES_XCBC_MAC_01"):
            result = False
    
    def test_qat_3DES_CBC_auto(self):
        result = True
        self.logger.info("Test qat_c_3DES_CBC_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_3DES_CBC_00"):
            result = False
            
    def test_qat_3DES_CTR_auto(self):
        result = True
        self.logger.info("Test qat_c_3DES_CTR_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_3DES_CTR_00"):
            result = False
      
    def test_qat_AES_GCM_AES_GCM(self):

        result = True

        self.logger.info("Test qat_ch_AES_GCM_AES_GCM_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_ch_AES_GCM_AES_GCM_01"):
            result = False
    
    def test_qat_AES_DOCSISBPI_auto(self):
        result = True
        self.logger.info("Test qat_ch_AES_DOCSISBPI")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_ch_AES_DOCSISBPI"):
            result = False
            
    def test_qat_c_DES_DOCSISBPI_auto(self):
        result = True
        self.logger.info("Test qat_c_DES_DOCSISBPI")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_DES_DOCSISBPI"):
            result = False
            
    def test_qat_SNOW3G_auto(self):

        result = True

        self.logger.info("Test qat_c_UEA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_UEA2_01"):
            result = False

        self.logger.info("Test qat_h_UIA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_UIA2_01"):
            result = False
        
        self.verify(result, True)
        
    def test_qat_KASUMI_auto(self):

        result = True
        self.logger.info("Test qat_kasumi_c_F8_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_kasumi_c_F8_01"):
            result = False

        self.logger.info("Test qat_kasumi_h_F9_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_kasumi_h_F9_01"):
            result = False

        self.verify(result, True)
        
    def test_qat_ZUC_auto(self):

        result = True
        self.logger.info("Test qat_c_EEA3_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_EEA3_01"):
            result = False

        self.logger.info("Test qat_h_EIA3_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_EIA3_01"):
            result = False
            
    def test_qat_c_NULL_auto(self):

        result = True

        self.logger.info("Test qat_c_NULL_auto")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "null_c_NULL_auto"):
            result = False

        self.verify(result, True)
                 
    def test_qat_h_NULL_auto(self):

        result = True

        self.logger.info("Test qat_h_NULL_auto")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_NULL_auto"):
            result = False

        self.verify(result, True)
          
    def test_aesni_mb_AES_CBC_auto(self):
        result = True
        self.logger.info("Test aesni_mb_c_AES_CBC_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "aesni_mb_c_AES_CBC_00"):
            result = False
        
    def test_aesni_mb_AES_CTR_auto(self):
        result = True
        self.logger.info("Test aesni_mb_c_AES_CTR_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "aesni_mb_c_AES_CTR_00"):
            result = False
            
    def test_aesni_mb_AES_DOCSISBPI_auto(self):
        result = True
        self.logger.info("Test aesni_mb_c_AES_DOCSISBPI")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "aesni_mb_c_AES_DOCSISBPI"):
            result = False
            
    def test_aesni_AES_GCM_AES_GCM(self):

        result = True

        self.logger.info("Test aesni_gcm_ch_AES_GCM_AES_GCM_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "aesni_gcm_ch_AES_GCM_AES_GCM_01"):
            result = False

        self.verify(result, True)
    
    def test_kasumi_KASUMI_auto(self):

        result = True
        self.logger.info("Test kasumi_c_F8_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "kasumi_c_F8_01"):
            result = False

        self.logger.info("Test kasumi_h_F9_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "kasumi_h_F9_01"):
            result = False

        self.verify(result, True)
            
    def test_null_NULL_CIPHER(self):

        result = True
        self.logger.info("Test null_c_NULL_auto")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "null_c_NULL_auto"):
            result = False

        self.verify(result, True)
      
    def test_null_NULL_HASH(self):

        result = True

        self.logger.info("Test null_h_NULL_auto")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "null_h_NULL_auto"):
            result = False

        self.verify(result, True)
        
    def test_null_c_NULL_auto(self):

        result = True

        self.logger.info("Test null_c_NULL_auto")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "null_c_NULL_auto"):
            result = False

        self.verify(result, True)
                 
    def test_null_h_NULL_auto(self):

        result = True

        self.logger.info("Test null_h_NULL_auto")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "null_h_NULL_auto"):
            result = False

        self.verify(result, True)

        
    def test_snow3g_SNOW3G(self):

        result = True

        self.logger.info("Test snow3g_c_UEA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "snow3g_c_UEA2_01"):
            result = False

        self.logger.info("Test snow3g_h_UIA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "snow3g_h_UIA2_01"):
            result = False

        self.verify(result, True)
    
    def test_zun_ZUC_auto(self):

        result = True
        self.logger.info("Test zuc_c_EEA3_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "zuc_c_EEA3_01"):
            result = False

        self.logger.info("Test zuc_h_EIA3_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "zuc_h_EIA3_01"):
            result = False
            
    # openssl pmd cases 
    def test_openssl_3DES_CBC_auto(self):
        result = True
        self.logger.info("Test openssl_c_3DES_CBC_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_c_3DES_CBC_00"):
            result = False
            
    def test_openssl_3DES_CTR_auto(self):
        result = True
        self.logger.info("Test openssl_c_3DES_CTR_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_c_3DES_CTR_00"):
            result = False   
                    
    def test_openssl_AES_CBC_auto(self):
        result = True
        self.logger.info("Test openssl_c_AES_CBC_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_c_AES_CBC_00"):
            result = False
            
    def test_openssl_AES_CTR_auto(self):
        result = True
        self.logger.info("Test openssl_c_AES_CTR_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_c_AES_CTR_00"):
            result = False
        
    def test_openssl_AES_GCM_auto(self):
        result = True
        self.logger.info("Test openssl_c_AES_GCM_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_c_AES_GCM_00"):
            result = False
    
    def test_openssl_h_MD_SHA_auto(self):
        result = True
        self.logger.info("Test openssl_h_MD_SHA_00")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_h_MD_SHA_00"):
            result = False
    
    def test_openssl_c_DES_DOCSISBPI_auto(self):
        result = True
        self.logger.info("Test openssl_c_DES_DOCSISBPI")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "openssl_c_DES_DOCSISBPI"):
            result = False
            
    def test_calculatr_case_number(self):
        
        self.__calculate_totall_cases_numb()
    
    def __calculate_totall_cases_numb(self):
        alg_map = {}
        pmd_map = {}
        map_combine  = {}
        count = 0
        alg = ""
        pmd = ""
        alg_list = ["AES_CBC","AES_CTR","AES_GCM","3DES_CBC", \
                   "3DES_CTR","SNOW3G","KASUMI","ZUC","NULL","MD_SHA"]
        pmd_list = ["qat","aesni_mb","aesni_gcm","snow3g",\
                   "kasumi","zuc","openssl","null"]
        valid_map = {
                    "qat": ["AES_CBC", "AES_CTR","AES_GCM","3DES_CBC", \
                            "3DES_CTR","SNOW3G","KASUMI","NULL","MD_SHA"],
                    "aesni_mb":["AES_CBC", "AES_CTR"],
                    "aesni_gcm":["AES_GCM"],
                    "snow3g":["SNOW3G"],
                    "kasumi":["KASUMI"],
                    "zuc":["ZUC"],
                    "openssl":["AES_CBC", "AES_CTR","AES_GCM","3DES_CBC","3DES_CTR","MD_SHA"],
                    "null":["NULL"]                    
                    }
        
        for index,value in test_vectors.iteritems():
            test_vector_list = self.__test_vector_to_vector_list(value,
                core_mask="-1",port_mask=self.port_mask)
            count = count + len(test_vector_list)
            for i in alg_list:
                if (index.upper()).find(i) != -1:
                    alg = i
                    if i in alg_map:
                        alg_map[i] += len(test_vector_list)
                    else:
                        alg_map[i] = len(test_vector_list)
            for j in pmd_list:
                if (index).find(j) != -1:
                    pmd = j if j !="" else "qat"
                    if i in pmd_map:
                        pmd_map[j] += len(test_vector_list)
                    else:
                        pmd_map[j] = len(test_vector_list)
            if alg in valid_map[pmd]:
                temp_str = pmd + "_" + alg
                if temp_str in map_combine:
                    map_combine[temp_str] += len(test_vector_list)
                else:
                    map_combine[temp_str] = len(test_vector_list)
        for k,v in alg_map.iteritems():
            self.logger.info("Total {name} cases:\t\t\t{number}".format(name=k,number=v))
        for k,v in pmd_map.iteritems():
            self.logger.info("Total {name} cases:\t\t\t{number}".format(name=k,number=v))
        for k,v in map_combine.iteritems():
            self.logger.info("Total {name} cases:\t\t\t{number}".format(name=k,number=v))
        self.logger.info("Total cases:\t\t\t {0}".format(count))
    
    
    def __execute_l2fwd_crypto_test(self, test_vectors, test_vector_name):

        if test_vector_name not in test_vectors:
            self.logger.warn("SKIP : " + test_vector_name)
            return True

        test_vector = test_vectors[test_vector_name]

        test_vector_list = self.__test_vector_to_vector_list(test_vector,
                core_mask=self.core_mask,
                port_mask=self.port_mask)

        result = True
        self.logger.info("Total Generated {0} Tests".format(len(test_vector_list)))
        for test_vector in test_vector_list:
            self.logger.debug(test_vector)
            cmd_str = self.__test_vector_to_cmd(test_vector,
                                                core_mask=self.core_mask,
                                                port_mask=self.port_mask)
            self.dut.send_expect(cmd_str, "==", 30)
            time.sleep(5)
            
            payload = self.__format_hex_to_list(test_vector["input"])

            inst = sniff_packets(self.rx_interface, timeout=5)

            PACKET_COUNT = 65
            pkt = Packet()
            pkt.assign_layers(["ether", "ipv4", "raw"])
            pkt.config_layer("ether", {"src":"52:00:00:00:00:00"})
            pkt.config_layer("ipv4", {"src":"192.168.1.1", "dst":"192.168.1.2"})
            pkt.config_layer("raw", {"payload":payload})
            pkt.send_pkt(tx_port=self.tx_interface, count=PACKET_COUNT)
            pkt.pktgen.pkt.show()

            pkt_rec = load_sniff_packets(inst)

            for pkt_r in pkt_rec:
                packet_hex = pkt_r.strip_element_layer4("load")
                cipher_text = binascii.b2a_hex(packet_hex)
                self.logger.info("Cipher text in packet = " + cipher_text)
                self.logger.info("Ref Cipher text       = " + test_vector["output_cipher"]) 
                if str.lower(cipher_text) == str.lower(test_vector["output_cipher"]):
                     self.logger.info(cipher_text)
                     self.logger.info("Cipher Matched.")
                else:
                    if test_vector["output_cipher"] != "":
                        result = False
                        self.logger.info("Cipher NOT Matched.")
                        self.logger.info("Cipher text in packet = " + cipher_text)
                        self.logger.info("Ref Cipher text       = " + test_vector["output_cipher"])
                    else:
                        self.logger.info("Skip Cipher, Since no cipher text set")

                hash_length = len(test_vector["output_hash"])/2
                if hash_length != 0:
                    hash_text = binascii.b2a_hex(pkt_r.pktgen.pkt["Padding"].getfieldval("load"))
                    self.logger.info("Hash text in packet = " + hash_text)
                    self.logger.info("Ref Hash text       = " + test_vector["output_hash"])
                    if str.lower(hash_text) == str.lower(test_vector["output_hash"]):
                        self.logger.info("Hash Matched")
                    else:
                        result = False
                        self.logger.info("Hash NOT Matched")
                        self.logger.info("Hash text in packet = " + hash_text)
                        self.logger.info("Ref Hash text       = " + test_vector["output_hash"])
                else:
                    self.logger.info("Skip Hash, Since no hash text set")

            self.logger.info("Packet Size :    %d " % (len(test_vector["input"]) / 2))
        if result:
            self.logger.info("PASSED")
        else:
            self.logger.info("FAILED")

        return result

    def tear_down(self):
        self.dut.kill_all()

    def tear_down_all(self):
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=y$/CONFIG_RTE_LIBRTE_PMD_QAT=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=y$/CONFIG_RTE_LIBRTE_PMD_KASUMI=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_OPENSSL=y$/CONFIG_RTE_LIBRTE_PMD_OPENSSL=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=n/' config/common_base", "# ") 
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_ZUC=y$/CONFIG_RTE_LIBRTE_PMD_ZUC=n/' config/common_base", "# ")
        
    def __get_tcpdump_cmd(self,interface):
        cmd = ""        
      
        status, output = commands.getstatusoutput("tcpdump --version")
        head = output.find('tcpdump version')
        strlen = len("tcpdump version ")
        tail = output.find("\nlibpcap version")
        version = output[head + strlen : tail]
        v =  int(version.replace('.',''))
        if v < 462 :
            cmd = "".join("tcpdump -P in -w %s.pcap -i %s &"%(interface,interface))
        else:
            cmd = "".join("tcpdump -Q in -w %s.pcap -i %s &"%(interface,interface))
        return cmd 
    
    def __test_vector_to_cmd(self, test_vector, core_mask="", port_mask=""):
        L2FWD_CRYPTO_APP = "./examples/l2fwd-crypto/build/app/l2fwd-crypto"
        EAL_CORE_MASK = " -cf" if core_mask == "" else " -c" + core_mask
        EAL_MM_CHANNEL = " -n4"
        EAL_SOCKET_MEM = " --socket-mem=512,512 "
        EAL_SEP = " --"
        PORT_MASK = "" if port_mask == "" else " -p" + port_mask
        QUEUE_NUM = ""

        vdev = ""
        if self.__check_field_in_vector(test_vector, "vdev"):
            vdev = " --vdev " + test_vector["vdev"]

        chain = ""
        if self.__check_field_in_vector(test_vector, "chain"):
            chain = " --chain " + test_vector["chain"]

        cdev_type = ""
        if self.__check_field_in_vector(test_vector, "cdev_type"):
            cdev_type = " --cdev_type " + test_vector["cdev_type"]

        cipher_algo = ""
        if self.__check_field_in_vector(test_vector, "cipher_algo"):
            cipher_algo = " --cipher_algo " + test_vector["cipher_algo"]

        cipher_op = ""
        if self.__check_field_in_vector(test_vector, "cipher_op"):
            cipher_op = " --cipher_op " + test_vector["cipher_op"]

        cipher_key = ""
        if self.__check_field_in_vector(test_vector, "cipher_key"):
            cipher_key = " --cipher_key " + self.__format_hex_to_param(test_vector["cipher_key"])

        iv = ""
        if self.__check_field_in_vector(test_vector, "iv"):
            iv = " --iv " + self.__format_hex_to_param(test_vector["iv"])

        auth_algo = ""
        if self.__check_field_in_vector(test_vector, "auth_algo"):
            auth_algo = " --auth_algo " + test_vector["auth_algo"]

        auth_op = ""
        if self.__check_field_in_vector(test_vector, "auth_op"):
            auth_op = " --auth_op " + test_vector["auth_op"]

        auth_key = ""
        if self.__check_field_in_vector(test_vector, "auth_key"):
            auth_key = " --auth_key " + self.__format_hex_to_param(test_vector["auth_key"])

        auth_key_random_size = ""
        if self.__check_field_in_vector(test_vector, "auth_key_random_size"):
            auth_key_random_size = " --auth_key_random_size " + test_vector["auth_key_random_size"]

        aad = ""
        if self.__check_field_in_vector(test_vector, "aad"):
            aad = " --aad " + self.__format_hex_to_param(test_vector["aad"])

        aad_random_size = ""
        if self.__check_field_in_vector(test_vector, "aad_random_size"):
            aad_random_size = " --aad_random_size " + test_vector["aad_random_size"]

        cmd_str = "".join([L2FWD_CRYPTO_APP, EAL_CORE_MASK, EAL_MM_CHANNEL,EAL_SOCKET_MEM, vdev, vdev, EAL_SEP,
                          PORT_MASK, QUEUE_NUM, chain, cdev_type, cipher_algo, cipher_op, cipher_key,
                          iv, auth_algo, auth_op, auth_key, auth_key_random_size, aad, aad_random_size])

        return cmd_str

    def __check_field_in_vector(self, test_vector, field_name):
        if field_name in test_vector and test_vector[field_name]:
            return True
        return False

    def __format_hex_to_param(self, hex_str, sep=":", prefix=""):
        if not hex_str:
            return ""
        if len(hex_str) == 1:
            return prefix + "0" + hex_str

        result = prefix + hex_str[0:2]
        for i in range(2, len(hex_str), 2):
            if len(hex_str) < i + 2:
                result = result + sep + "0" + hex_str[i:]
            else:
                result = result + sep + hex_str[i:i+2]

        return result

    def __format_hex_to_list(self, hex_str):
        if not hex_str:
            return []
        if len(hex_str) == 1:
            return [hex_str]

        result = []
        result.append(hex_str[0:2])
        for i in range(2, len(hex_str), 2):
            if len(hex_str) < i + 2:
                result.append(hex_str[i:])
            else:
                result.append(hex_str[i:i+2])
        return result

    def __gen_input(self, length, pattern=None):
        pattern = "11"
        input_str = ""
        for i in range(length):
            input_str += pattern
        return input_str

    def __gen_key(self, length, pattern=None, mask="000000"):
        base_key = "000102030405060708090a0b0c0d0e0f"
        key = ""
        n = length // 16
        for i in range(n):
            key = key + base_key
            base_key = base_key[2:] + base_key[0:2]
        m = length % 16
        key = key + base_key[0:2*m]
        return key
    
    def __cryptography_cipher(self, vector):
        key = binascii.a2b_hex(vector["cipher_key"])
        iv = binascii.a2b_hex(vector["iv"])
        cipher_algo_str = vector["cipher_algo"]
        if vector["cipher_algo"] == "AES_CBC":
            cipher_algo = algorithms.AES(key)
            cipher_mode = modes.CBC(iv)
        elif vector["cipher_algo"] == "AES_CTR":
            cipher_algo = algorithms.AES(key)
            cipher_mode = modes.CTR(iv)
        elif vector["cipher_algo"] == "3DES_CBC":
            cipher_algo = algorithms.TripleDES(key)
            cipher_mode = modes.CBC(iv)
        elif vector["cipher_algo"] == "AES_GCM":
            cipher_algo = algorithms.AES(key)
            cipher_mode = modes.GCM(iv)
        else:
            cipher_algo = algorithms.AES(key)
            cipher_mode = modes.CBC(iv)

        cipher = Cipher(cipher_algo, cipher_mode, backend=default_backend())
        encryptor = cipher.encryptor()
        cipher_text = encryptor.update(binascii.a2b_hex(vector["input"])) + encryptor.finalize()

        return binascii.b2a_hex(cipher_text)

    def __CryptoMoble_cipher(self,vector):
        # default is kasumi , kasumi alg we need to guarantee IV is :0001020304000000
        #so count is 66051 , dir =1 , bearer = 0 
        cipher_str = ""  
        out_str = ""    
        cipher_algo = vector['cipher_algo']

        mBitlen = 8 * (len(vector['input']) / 2)        
        bin_input = bytearray.fromhex(vector["input"])
        str_input = str(bin_input)
        bin_key = binascii.a2b_hex(vector["cipher_key"])
        if ((cipher_algo.upper()).find("KASUMI") != -1):     
            vector["iv"] = vector["iv"][:10] + "000000"             
            out_str = cm.UEA1(key=bin_key,count=66051, bearer=0, \
                           dir=1,data=str_input,bitlen=mBitlen)   
           
        elif ((cipher_algo.upper()).find("SNOW3G") != -1):

            vector["iv"] = "00000000000000000000000000000000"
            out_str = cm.UEA2(key=bin_key,count=0,bearer=0,dir=0, \
                           data=str_input,bitlen=mBitlen)
            
        elif ((cipher_algo.upper()).find("ZUC") != -1):
            vector["iv"] = "00010203040000000001020304000000"  
            out_str = cm.EEA3(key=bin_key,count=0x10203,bearer=0,dir=1, \
                           data=str_input,bitlen=mBitlen)                      
           
        cipher_str = out_str.encode("hex").upper()
            
        return cipher_str
            
    def __gen_null_cipher_out(self,vector):
        cipher_str = ""
        if (vector['chain'] == "CIPHER_ONLY") or (vector['chain'] == "CIPHER_HASH"):
            cipher_str  = vector['input']
        elif (vector['chain'] == "HASH_CIPHER"):
            cipher_str  = vector['output_hash']
        return cipher_str 
           
    def __gen_cipher_output(self, vector):
        #import pdb
        #pdb.set_trace()
        if vector["chain"] == "HASH_ONLY":
            vector["output_cipher"] == ""
            return

        if vector["output_cipher"] != "*":
            return
        
        cipher_str = ""
        ####
        if(((vector['cipher_algo']).upper()).find("KASUMI") != -1) or  \
                (((vector['cipher_algo']).upper()).find("SNOW3G") != -1) or \
                (((vector['cipher_algo']).upper()).find("ZUC") != -1):
            cipher_str = self.__CryptoMoble_cipher(vector)
        elif (vector['cipher_algo'] == "NULL"):
            cipher_str = self.__gen_null_cipher_out(vector)
        else:
            cipher_str = self.__cryptography_cipher(vector)
        vector["output_cipher"] = cipher_str.upper()
    
    def __gen_kasumi_hash(self,vector):
        auth_str = ""     
        auth_algo = vector['auth_algo']   
        mBitlen = 8 * (len(vector['input']) / 2)     
        bin_input = bytearray.fromhex(vector["input"])
        str_input = str(bin_input)
        bin_key = binascii.a2b_hex(vector["auth_key"])
         
        #vector["add"] = vector["add"][:6] + "000000"      
        #ADD IS 0001020304050607      
        hash_out = cm.UIA1(key=bin_key,count=0X10203, fresh=0X4050607,dir=0, \
                        data=str_input)            
        auth_str = hash_out.encode("hex").upper()                                              
            
        return auth_str
    
    def __gen_snow3g_hash(self,vector):
        auth_str = ""     
        auth_algo = vector['auth_algo']
        mBitlen = 8 * (len(vector['input']) / 2) 
        bin_input = bytearray.fromhex(vector["input"])
        str_input = str(bin_input)
        bin_key = binascii.a2b_hex(vector["auth_key"])
        #ADD IS  00010203040506070001020304050607
        vector["aad"] = "00000000000000000000000000000000"
        #vector["aad"][:16] + vector["aad"][:16]      
               
        hash_out = cm.UIA2(key=bin_key,count=0, fresh=0,dir=0, \
                        data=str_input)  
        
        #hash_out = cm.UIA2(key=bin_key,count=0x7060504, fresh=0x3020100,dir=0, \
         #               data=str_input)            
        auth_str = hash_out.encode("hex").upper()                                              
            
        return auth_str
    
    def __gen_zuc_hash(self,vector):
        auth_str = ""     
        auth_algo = vector['auth_algo']
        mBitlen = 8 * (len(vector['input']) / 2) 
        bin_input = bytearray.fromhex(vector["input"])
        str_input = str(bin_input)
        bin_key = binascii.a2b_hex(vector["auth_key"])
        
        #add is 00010203080000000001020308000000
        #vector["aad"] = vector["aad"][:8] + "08000000" + vector["aad"][:8] + "08000000"     
        vector["aad"] = "00000000000000000000000000000000"
        hash_out = cm.EIA3(key=bin_key,count=0, bearer=0,dir=0,data=str_input,bitlen=mBitlen)            
        auth_str = hash_out.encode("hex").upper()                                              
            
        return auth_str
    
    def __gen_null_hash(self,vector):
        auth_str =  ""
        if (vector['chain'] == "HASH_ONLY") or (vector['chain'] == "HASH_CIPHER"):
            auth_str  = vector['input']
        elif (vector['chain'] == "CIPHER_HASH"):
            auth_str  = vector['output_cipher']
        return auth_str 
    
    def __gen_hash_output(self, vector):
        if vector["chain"] == "CIPHER_ONLY":
            vector["output_hash"] == ""
            return
           
        if vector["output_hash"] != "*":
            return

        if vector["chain"] == "HASH_ONLY":
            vector["output_cipher"] = ""
 
        hash_str = ""

        if vector["chain"] == "CIPHER_HASH":
            input_str = vector["output_cipher"]
        else:
            input_str = vector["input"]
        
        auth_algo = vector["auth_algo"]
        if auth_algo == "MD5_HMAC":
            hash_str = hmac.new(binascii.a2b_hex(vector["auth_key"]),\
                    binascii.a2b_hex(input_str), hashlib.md5).hexdigest()
        elif auth_algo == "SHA1_HMAC":
            hash_str = hmac.new(binascii.a2b_hex(vector["auth_key"]),\
                    binascii.a2b_hex(input_str), hashlib.sha1).hexdigest()
        elif auth_algo == "SH224_HMAC":
            hash_str = hmac.new(binascii.a2b_hex(vector["auth_key"]),\
                    binascii.a2b_hex(input_str), hashlib.sha224).hexdigest()
        elif auth_algo == "SH256_HMAC":
            hash_str = hmac.new(binascii.a2b_hex(vector["auth_key"]),\
                    binascii.a2b_hex(input_str), hashlib.sha256).hexdigest()
        elif auth_algo == "SHA384_HMAC":
            hash_str = hmac.new(binascii.a2b_hex(vector["auth_key"]),\
                    binascii.a2b_hex(input_str), hashlib.sha384).hexdigest()
        elif auth_algo == "SHA512_HMAC":
            hash_str = hmac.new(binascii.a2b_hex(vector["auth_key"]),\
                    binascii.a2b_hex(input_str), hashlib.sha512).hexdigest()
        elif auth_algo == "AES_XCBC_MAC":
            pass
        elif auth_algo == "AES_GCM":
            pass
        elif auth_algo == "AES_GMAC":
            pass
        elif auth_algo == "SNOW3G_UIA2":
            hash_str = self.__gen_snow3g_hash(vector)
        elif auth_algo == "ZUC_EIA3":
            hash_str = self.__gen_zuc_hash(vector)
        elif auth_algo == "KASUMI_F9":
            hash_str = self.__gen_kasumi_hash(vector)
        elif auth_algo == "NULL":
            hash_str = self.__gen_null_hash(vector)
        elif auth_algo == "MD5":
             hash_str = hashlib.md5(binascii.a2b_hex(vector["auth_key"])).hexdigest() 
        elif auth_algo == "SHA1":
            hash_str = hashlib.sha1(binascii.a2b_hex(vector["auth_key"])).hexdigest() 
        elif auth_algo == "SHA224":
            hash_str = hashlib.sha224(binascii.a2b_hex(vector["auth_key"])).hexdigest() 
        elif auth_algo == "SHA256":
            hash_str = hashlib.sha256(binascii.a2b_hex(vector["auth_key"])).hexdigest() 
        elif auth_algo == "SHA384":
            hash_str = hashlib.sha384(binascii.a2b_hex(vector["auth_key"])).hexdigest() 
        elif auth_algo == "SHA512":
            hash_str = hashlib.sha512(binascii.a2b_hex(vector["auth_key"])).hexdigest() 
        else:
            pass
        vector["output_hash"] =  hash_str.upper()
        self.__actually_aesni_mb_digest(vector)

    def __gen_output(self, vector, cmds, core_mask="", port_mask=""):
        if core_mask != "-1":
            self.__gen_cipher_output(vector)
            self.__gen_hash_output(vector)
        cmds.append(vector)

    def __var2list(self, var):
        var_list = var if isinstance(var, list) else [var]
        return var_list

    def __is_valid_op(self, chain, op):
        chain_op_map = {
                "CIPHER_ONLY": ["ENCRYPT", "DECRYPT"],
                "HASH_ONLY": ["GENERATE", "VERIFY"],
                "CIPHER_HASH": ["ENCRYPT", "GENERATE"],
                "HASH_CIPHER": ["DECRYPT", "VERIFY"],
                }
        if op in chain_op_map[chain]:
            return True
        return False

    def __is_valid_size(self, key_type, algo, size):
        algo_size_map = {
                "AES_CBC": {
                    "cipher_key": [16, 24, 32],
                    "iv": [16],
                    },
                "SHA1_HMAC": {
                    "auth_key": [64],
                    "aad": [0]
                    },
            
                "aes-cbc": {
                    "cipher_key": [16, 24, 32],
                    "iv": [16],
                    },
                "aes-ctr": {
                    "cipher_key": [16, 24, 32],
                    "iv": [16]
                    },
                "3des-cbc": {
                    "cipher_key": [16, 24],
                    "iv": [8]
                    },
                "3des-ctr": {
                    "cipher_key": [16, 24],
                    "iv": [8]
                    },
                "aes-gcm": {
                    "cipher_key": [16, 24, 32],
                    "auth_key": [16, 24, 32],
                    "aad": [0,1,2,3,4,5,6,8,9,12,16,24,32,64,128,155,256,1024,65535],
                    "iv": [12,16]
                    },
                "aes-docsisbpi":{
                    "cipher_key": [16],
                    "iv": [16],
                    },
                "des-docsisbpi":{
                    "cipher_key": [8],
                    "iv": [8],
                    },
                "snow3g-uea2": {
                    "cipher_key": [16],
                    "iv": [16]
                    },
                "kasumi-f8": {
                    "cipher_key": [16],
                    "iv": [8]
                    },
                "zuc-eea3": {
                    "cipher_key": [16],
                    "iv": [16]
                    },
                "null": {
                    "cipher_key": [0],
                    "auth_key": [0],
                    "aad": [0],
                    "iv": [0]
                    },                        
                "md-hmac": {
                    "auth_key": [64],
                    "aad": [0],
                    },
                "sha1-hmac": {
                    "auth_key": [64],
                    "aad": [0]
                    },
                "sha2-224-hmac": {
                    "auth_key": [64],
                    "aad": [0]
                    },
                "sha2-256-hmac": {
                    "auth_key": [64],
                    "aad": [0]
                    },
                "sha2-384-hmac": {
                    "auth_key": [128],
                    "aad": [0]
                    },
                "sha2-512-hmac": {
                    "auth_key": [128],
                    "aad": [0]
                    },
                "AES_XCBC_MAC": {
                    "auth_key": [16],
                    "aad": [0]
                    },
                "aes-gmac": {
                    "auth_key": [16, 24, 32],
                    "aad": [1, 16, 64, 128, 256, 65535]
                    },
                "snow-uia2": {
                    "auth_key": [16],
                    "aad": [16]
                    },
                "kasumi-f9": {
                    "auth_key": [16],
                    "aad": [8]
                    },
                "zuc-eia3": {
                    "auth_key": [16],
                    "aad": [16]
                    },
                "md5": {
                    "auth_key": [0],
                    "aad": [0],
                    },
                "sha1": {
                    "auth_key": [0],
                    "aad": [0]
                    },
                "sha2-224": {
                    "auth_key": [0],
                    "aad": [0]
                    },
                "sha2-256": {
                    "auth_key": [0],
                    "aad": [0]
                    },
                "sha2-384": {
                    "auth_key": [0],
                    "aad": [0]
                    },
                "sha2-512": {
                    "auth_key": [0],
                    "aad": [0]
                    },
                }
        result = False
        if algo in algo_size_map:
            if key_type in algo_size_map[algo]:
                if size in algo_size_map[algo][key_type]:
                    result = True
        return result
    
    def __actually_aesni_mb_digest(self,vector):

        if ((vector["vdev"]).find("crypto_aesni_mb") == -1):
            return
        
        auth_algo_dgst_map = {
                "md4-hmac": 12,
                "sha1-hmac": 12,
                "sha2-224-hamc": 14,
                "sha2-256-hmac": 16,
                "sha2-384-hamc": 24,
                "sha2-512-hmac": 32,
                "AES_XCBC_MAC": 12
                }
        if vector["auth_algo"] in auth_algo_dgst_map:
            digest = auth_algo_dgst_map[vector["auth_algo"]]
            vector["output_hash"] = vector["output_hash"] if digest >= (len(vector["output_hash"]) / 2) \
                    else (vector["output_hash"])[0:2*digest]
        
        
    def __iter_cipher_algo(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "HASH_ONLY":
            test_vector["cipher_algo"] = ""
            self.__iter_cipher_op(test_vector, vector_list, core_mask, port_mask)
        else:
            cipher_algo_list = self.__var2list(test_vector["cipher_algo"])
            for cipher_algo in cipher_algo_list:
                test_vector = vector.copy()
                test_vector["cipher_algo"] = cipher_algo
                self.__iter_cipher_op(test_vector, vector_list, core_mask, port_mask)

    def __iter_cipher_op(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "HASH_ONLY":
            test_vector["cipher_op"] = ""
            self.__iter_cipher_key(test_vector, vector_list, core_mask, port_mask)
        else:
            cipher_op_list = self.__var2list(test_vector["cipher_op"])
            for cipher_op in cipher_op_list:
                if self.__is_valid_op(test_vector["chain"], cipher_op):
                    test_vector = vector.copy()
                    test_vector["cipher_op"] = cipher_op
                    self.__iter_cipher_key(test_vector, vector_list, \
                            core_mask, port_mask)

    def __iter_cipher_key(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "HASH_ONLY":
            test_vector["cipher_key"] = ""
            self.__iter_iv(test_vector, vector_list, core_mask, port_mask)
        else:
            cipher_key_list = self.__var2list(test_vector["cipher_key"])
            for cipher_key in cipher_key_list:
                test_vector = vector.copy()
                if isinstance(cipher_key, int):
                    if self.__is_valid_size("cipher_key", \
                            test_vector["cipher_algo"], \
                            cipher_key):
                        test_vector["cipher_key"] = self.__gen_key(cipher_key)
                        self.__iter_iv(test_vector, vector_list, core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["cipher_key"] = cipher_key
                    self.__iter_iv(test_vector, vector_list, core_mask, port_mask)

    def __iter_iv(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "HASH_ONLY":
            test_vector["iv"] = ""
            self.__iter_auth_algo(test_vector, vector_list, core_mask, port_mask)
        else:
            iv_list = self.__var2list(test_vector["iv"])
            for iv in iv_list:
                test_vector = vector.copy()
                if isinstance(iv, int):
                    if self.__is_valid_size("iv", \
                            test_vector["cipher_algo"], \
                            iv):
                        test_vector["iv"] = self.__gen_key(iv)
                        self.__iter_auth_algo(test_vector, vector_list, \
                                core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["iv"] = iv
                    self.__iter_auth_algo(test_vector, vector_list, \
                            core_mask, port_mask)

    def __iter_auth_algo(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "CIPHER_ONLY":
            test_vector["auth_algo"] = ""
            self.__iter_auth_op(test_vector, vector_list, core_mask, port_mask)
        else:
            auth_algo_list = self.__var2list(test_vector["auth_algo"])
            for auth_algo in auth_algo_list:
                test_vector = vector.copy()
                test_vector["auth_algo"] = auth_algo
                self.__iter_auth_op(test_vector, vector_list, core_mask, port_mask)

    def __iter_auth_op(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "CIPHER_ONLY":
            test_vector["auth_op"] = ""
            self.__iter_auth_key(test_vector, vector_list, core_mask, port_mask)
        else:
            auth_op_list = self.__var2list(test_vector["auth_op"])
            for auth_op in auth_op_list:
                if self.__is_valid_op(test_vector["chain"], auth_op):
                    test_vector = vector.copy()
                    test_vector["auth_op"] = auth_op 
                    self.__iter_auth_key(test_vector, vector_list, \
                            core_mask, port_mask)

    def __iter_auth_key(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "CIPHER_ONLY":
            test_vector["auth_key"] = ""
            self.__iter_aad(test_vector, vector_list, core_mask, port_mask)
        else:
            auth_key_list = self.__var2list(test_vector["auth_key"])
            for auth_key in auth_key_list:
                test_vector = vector.copy()
                if isinstance(auth_key, int):
                    if self.__is_valid_size("auth_key", \
                            test_vector["auth_algo"], \
                            auth_key):
                        test_vector["auth_key"] = self.__gen_key(auth_key)
                        self.__iter_aad(test_vector, vector_list, core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["auth_key"] = auth_key 
                    self.__iter_aad(test_vector, vector_list, core_mask, port_mask)

    def __iter_aad(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["chain"] == "CIPHER_ONLY":
            test_vector["aad"] = ""
            self.__iter_input(test_vector, vector_list, core_mask, port_mask)
        else:
            aad_list = self.__var2list(test_vector["aad"])
            for aad in aad_list:
                test_vector = vector.copy()
                if isinstance(aad, int):
                    if self.__is_valid_size("aad", \
                            test_vector["auth_algo"], \
                            aad):
                        test_vector["aad"] = self.__gen_key(aad)
                        self.__iter_input(test_vector, vector_list, \
                                core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["aad"] = aad
                    self.__iter_input(test_vector, vector_list, \
                            core_mask, port_mask)

    def __iter_input(self, vector, vector_list, core_mask="", port_mask=""):
        input_list = self.__var2list(vector["input"])
        for input_data in input_list:
            test_vector = vector.copy()
            test_vector["input"] = self.__gen_input(input_data) \
                    if isinstance(input_data, int) else input_data
                            
            self.__gen_output(test_vector, vector_list, core_mask, port_mask)

    def __test_vector_to_vector_list(self, test_vector,core_mask="", port_mask=""):
        vector_list = []
        
        chain_list = self.__var2list(test_vector["chain"])
 
        for chain in chain_list:
            test_vector["chain"] = chain
            self.__iter_cipher_algo(test_vector, vector_list, core_mask, port_mask)
        return vector_list


test_vectors = {

    "qat_c_AES_CBC_00": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-cbc"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24, 32],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128, 129,256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
     "qat_c_AES_CTR_00": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-ctr"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24, 32],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
            
    "qat_c_AES_GCM_00": {
        "vdev": "",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-gcm"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [12,16],
        "auth_algo": ["aes-gcm","aes-gmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128, 129,256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
        
    "qat_h_MD_SHA_00": {
        "vdev": "",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
     "qat_h_AES_XCBC_MAC_01": {
        "vdev": "",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["AES_XCBC_MAC"],
        "auth_op": "GENERATE",
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
    
    "qat_c_3DES_CBC_00": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["3des-cbc"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24],
        "iv": [8],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
    "qat_c_3DES_CTR_00": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["3des-ctr"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24],
        "iv": [8],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
     "qat_c_AES_GCM_01": {
        "vdev": "",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-gcm"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [12,16],
        "auth_algo": ["aes-gcm"],
        "auth_op": ["GENERATE"],
        "auth_key": [16, 24, 32],
        "auth_key_random_size": "",
        "aad": [8,12],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
    
    "qat_ch_AES_GCM_AES_GCM_01": {
        "vdev": "",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-gcm"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [12,16],
        "auth_algo": ["aes-gcm"],
        "auth_op": ["GENERATE"],
        "auth_key": [16, 24, 32],
        "auth_key_random_size": "",
        "aad": [8,12],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
          
    "qat_ch_AES_DOCSISBPI": {
        "vdev": "",
        "chain": ["CIPHER_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "aes-docsisbpi",
        "cipher_op": ["ENCRYPT","DECRYPT"],
        "cipher_key": [16],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[15,16,17,129,256,258,515,772,1019,1547,2011,2048],
        "output_cipher":"*",
        "output_hash": "*"
    },
          
    "qat_c_DES_DOCSISBPI": {
        "vdev": "",
        "chain": ["CIPHER_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "des-docsisbpi",
        "cipher_op": ["ENCRYPT","DECRYPT"],
        "cipher_key": [8],
        "iv": [8],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input":[5,8,11,16,64,127,258,506,512,521,1020,1022,1024],
        "output_cipher":"*",
        "output_hash": "*"
    },            
    "qat_c_UEA2_01": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["snow3g-uea2"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [16],
        "auth_algo": ["snow3g-uia2"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "qat_h_UIA2_01": {
        "vdev": "",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["snow3g-uia2"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
          
    "qat_kasumi_c_F8_01": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["kasumi-f8"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [8],
        "auth_algo": ["kasumi-f9"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [8],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "qat_kasumi_h_F9_01": {
        "vdev": "",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["kasumi-f9"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [8],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },   
        
    "qat_c_EEA3_01": {
        "vdev": "",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["zuc-eea3"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [16],
        "auth_algo": ["zuc-eia3"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "qat_h_EIA3_01": {
        "vdev": "",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["zuc-eia3"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
                 
    "qat_c_NULL_auto": {
        "vdev": "",
        "chain": ["CIPHER_ONLY","CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["null"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [0],
        "iv": "",
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "digest": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
       
    "qat_h_NULL_auto": {
        "vdev": "",
        "chain": ["CIPHER_ONLY","CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["null","aes-cbc","aes-ctr","3des-ctr","snow3g-uea2","kasumi-f8"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [8, 16, 24, 32, 40, 48, 56, 64],
        "iv": "",
        "auth_algo": ["null"],
        "auth_op": ["GENERATE"],
        "auth_key": [0],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "digest": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    }, 
        
    "aesni_mb_c_AES_CBC_00": {
        "vdev": "crypto_aesni_mb,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-cbc"],
        "cipher_op": ["ENCRYPT"],
        "cipher_key": [16, 24, 32],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
            "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
            "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128], 
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
     "aesni_mb_c_AES_CTR_00": {
        "vdev": "crypto_aesni_mb,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-ctr"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24, 32],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128, 129,256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
          
    "aesni_mb_c_AES_DOCSISBPI": {
        "vdev": "crypto_aesni_mb,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "aes-docsisbpi",
        "cipher_op": ["ENCRYPT","DECRYPT"],
        "cipher_key": [16],
        "iv": [16],
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input":[15,16,17,129,256,258,515,772,1019,1547,2011,2048],
        "output_cipher":"*",
        "output_hash": "*"
    },
                                              
    "null_c_NULL_01": {
        "vdev": "crypto_null_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY","CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["null"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": ["0"],
        "iv": "",
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "digest": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "null_h_NULL": {
        "vdev": "crypto_null_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": [0],
        "iv": "",
        "auth_algo": ["null"],
        "auth_op": ["GENERATE"],
        "auth_key": [0],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "digest": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
                    
    "null_c_NULL_auto": {
        "vdev": "crypto_null_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY","CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["null"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [0],
        "iv": [0],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [0,8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "digest": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },          
       
    "null_h_NULL_auto": {
        "vdev": "crypto_null_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY","CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["null"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [0,8, 16, 24, 32, 40, 48, 56, 64],
        "iv": [0],
        "auth_algo": ["null"],
        "auth_op": ["GENERATE"],
        "auth_key": [0],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "digest": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    }, 
             
                            
    "aesni_gcm_ch_AES_GCM_AES_GCM_01": {
        "vdev": "crypto_aesni_gcm_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-gcm"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [12,16],
        "auth_algo": ["aes-gcm"],
        "auth_op": ["GENERATE"],
        "auth_key": [16, 24, 32],
        "auth_key_random_size": "",
        "aad": [8,12],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
    
    
                
    "kasumi_c_F8_01": {
        "vdev": "crypto_kasumi_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["kasumi-f8"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [8],
        "auth_algo": ["kasumi-f9"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [8],
        "aad_random_size": "",
        "input": [16,48,64, 128, 129,256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "kasumi_h_F9_01": {
        "vdev": "crypto_kasumi_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["kasumi-f9"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [8],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
    
    "snow3g_c_UEA2_01": {
        "vdev": "crypto_snow3g_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["sno3g-uea2"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [16],
        "auth_algo": ["snow3g-uia2"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "snow3g_h_UIA2_01": {
        "vdev": "crypto_snow3g_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["snow3g-uia2"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },   
    
    "zuc_c_EEA3_01": {
        "vdev": "crypto_zuc_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["zuc-eea3"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [16],
        "auth_algo": ["zuc-eia3"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },

    "zuc_h_EIA3_01": {
        "vdev": "crypto_zuc_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["zuc-eia3"],
        "auth_op": ["GENERATE"],
        "auth_key": [16],
        "auth_key_random_size": "",
        "aad": [16],
        "aad_random_size": "",
        "input": [16,48,64, 128,129, 256, 512, 1024],
        "output_cipher": "*",
        "output_hash": "*"
    },
                
    "openssl_c_3DES_CBC_00": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["3des-cbc"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24],
        "iv": [8],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
    "openssl_c_3DES_CTR_00": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["3des-ctr"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24],
        "iv": [8],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128, 129,256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
    
    "openssl_c_AES_CBC_00": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-cbc"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24, 32],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
     "openssl_c_AES_CTR_00": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY", "CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-ctr"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16, 24, 32],
        "iv": [16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
            
    "openssl_c_AES_GCM_00": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_HASH"],
        "cdev_type": "ANY",
        "cipher_algo": ["aes-gcm"],
        "cipher_op": ["ENCRYPT", "DECRYPT"],
        "cipher_key": [16],
        "iv": [12,16],
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128, 129,256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
        
    "openssl_h_MD_SHA_00": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["HASH_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": ["md5", "sha1", "sha2-224", "sha2-256","sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth_op": ["GENERATE"],
        "auth_key": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth_key_random_size": "",
        "aad": [0],
        "aad_random_size": "",
        "input":[16,48,64, 128,129, 256, 512, 1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                
    "openssl_c_DES_DOCSISBPI": {
        "vdev": "crypto_openssl_pmd,socket_id=1,max_nb_sessions=128",
        "chain": ["CIPHER_ONLY"],
        "cdev_type": "ANY",
        "cipher_algo": "des-docsisbpi",
        "cipher_op": ["ENCRYPT","DECRYPT"],
        "cipher_key": [8],
        "iv": [8],
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input":[5,8,11,16,64,127,258,506,512,521,1020,1022,1024],
        "output_cipher":"*",
        "output_hash": "*"
    },
                            
}
