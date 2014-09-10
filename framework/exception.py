# <COPYRIGHT_TAG>

"""
User-defined exceptions used across the framework.
"""


class TimeoutException(Exception):

    """
    Command execution timeout.
    """

    def __init__(self, command, output):
        self.command = command
        self.output = output

    def __str__(self):
        msg = 'TIMEOUT on %s' % (self.command)
        return msg


class VerifyFailure(Exception):

    """
    To be used within the test cases to verify if a command output
    is as it was expected.
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SSHConnectionException(Exception):

    """
    SSH connection error.
    """

    def __init__(self, host):
        self.host = host

    def __str__(self):
        return 'Error trying to connect with %s' % self.host
