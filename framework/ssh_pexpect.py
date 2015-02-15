import time
import pexpect
import pxssh
from exception import TimeoutException, SSHConnectionException

"""
Module handle ssh sessions between tester and DUT.
Implement send_expect function to send command and get output data.
Aslo support transfer files to tester or DUT.
"""


class SSHPexpect(object):

    def __init__(self, host, username, password):
        try:
            self.session = pxssh.pxssh()
            self.username = username
            self.host = host
            self.password = password
            self.session.login(self.host, self.username,
                               self.password, original_prompt='[$#>]')
            self.send_expect('stty -echo', '# ', timeout=2)
        except Exception:
            raise SSHConnectionException(host)

    def init_log(self, logger, name):
        self.logger = logger
        self.logger.config_execution(name)
        self.logger.info("ssh %s@%s" % (self.username, self.host))

    def send_expect_base(self, command, expected, timeout=15):
        self.session.PROMPT = expected
        self.__sendline(command)
        self.__prompt(command, timeout)
        return self.get_output_before()

    def send_expect(self, command, expected, timeout=15, verify=False):
        ret = self.send_expect_base(command, expected, timeout)
        if verify:
            ret_status = self.send_expect_base("echo $?", expected)
            if not int(ret_status):
                return ret
            else:
                self.logger.error("Command: %s failure!" % command)
                return -1
        else:
            return ret

    def __prompt(self, command, timeout):
        if not self.session.prompt(timeout):
            raise TimeoutException(command, self.get_output_all())

    def __sendline(self, command):
        if len(command) == 2 and command.startswith('^'):
            self.session.sendcontrol(command[1])
        else:
            self.session.sendline(command)

    def get_output_before(self):
        self.session.flush()
        before = self.session.before.rsplit('\r\n', 1)
        if before[0] == "[PEXPECT]":
            before[0] = ""

        return before[0]

    def get_output_all(self):
        self.session.flush()
        output = self.session.before
        output.replace("[PEXPECT]", "")
        return output

    def close(self):
        if self.isalive():
            self.session.logout()

    def isalive(self):
        return self.session.isalive()

    def copy_file_from(self, src, dst = ".", password=''):
        """
        Copies a file from a remote place into local.
        """
        command = 'scp {0}@{1}:{2} {3}'.format(self.username, self.host, src, dst)
        if password == '':
            self._spawn_scp(command, self.password)
        else:
            self._spawn_scp(command, password)

    def copy_file_to(self, src, dst = "~/", password=''):
        """
        Sends a local file to a remote place.
        """
        command = 'scp {0} {1}@{2}:{3}'.format(src, self.username, self.host, dst)
        if password == '':
            self._spawn_scp(command, self.password)
        else:
            self._spawn_scp(command, password)

    def _spawn_scp(self, scp_cmd, password):
        """
        Transfer a file with SCP
        """
        self.logger.info(scp_cmd)
        p = pexpect.spawn(scp_cmd)
        time.sleep(0.5)
        ssh_newkey = 'Are you sure you want to continue connecting'
        i = p.expect([ssh_newkey, 'password: ', "# ", pexpect.EOF,
                      pexpect.TIMEOUT], 120)
        if i == 0:  # add once in trust list
            p.sendline('yes')
            i = p.expect([ssh_newkey, '[pP]assword: ', pexpect.EOF], 2)

        if i == 1:
            time.sleep(0.5)
            p.sendline(password)
            p.expect("100%", 60)
        if i == 4:
            self.logger.error("SCP TIMEOUT error %d" % i)

        p.close()
