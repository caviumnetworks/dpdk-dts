# <COPYRIGHT_TAG>

from ssh_pexpect import SSHPexpect
from settings import USERNAME


class SSHConnection(object):

    """
    Module for create session to host.
    Implement send_expect/copy function upper SSHPexpet module.
    """

    def __init__(self, host, session_name):
        self.session = SSHPexpect(host, USERNAME)
        self.name = session_name

    def init_log(self, logger):
        self.logger = logger
        self.logger.config_execution(self.name)
        self.session.init_log(logger, self.name)

    def send_expect(self, cmds, expected, timeout=15):
        self.logger.info(cmds)
        out = self.session.send_expect(cmds, expected, timeout)
        self.logger.debug(out)
        return out

    def close(self):
        self.session.close()

    def isalive(self):
        return self.session.isalive()

    def copy_file_from(self, filename, password=''):
        self.session.copy_file_from(filename, password)

    def copy_file_to(self, filename, password=''):
        self.session.copy_file_to(filename, password)
