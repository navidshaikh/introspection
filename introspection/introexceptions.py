import json
import os

PROBE_CONFIG = "probe_execution_errors.json"

try:
    PROBE_ERRORS = json.load(
        open(os.path.join("/etc/introspection/", PROBE_CONFIG)))
except IOError:
    filename = os.path.join(os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))),
                            "etc/introspection/",
                            PROBE_CONFIG)
    PROBE_ERRORS = json.load(open(filename))


class CustomCTSException(Exception):
    """
    Abstracted exception
    """
    def __init__(self, msg=""):
        self.msg = msg
        self.process_exception()
        self.exit_status = 1

    def process_exception(self):
        """
        This method process the exception and adds respective fields in error
        detail
        """
        self.exception_name = self.__class__.__name__
        self.error_detail = PROBE_ERRORS[self.exception_name]
        # Modify message if any
        self.error_detail["error_summary"] = self.error_detail[
            "error_summary"] + self.msg
        # new field apart from configuration file having backtrace detail
        self.error_detail["error_details"] = ""

    def get_exit_status(self):
        """
        Returns the exit status for particular exception
        """
        return self.exit_status

    def get_error_message(self):
        """
        Returns the error message for particular exception
        """
        return self.error_detail["error_summary"]

    def get_error_detail(self):
        """
        Returns the error detail for particular exception
        """
        return self.error_detail

    def __str__(self):
        return self.get_error_message()


class CTSDockerServiceNotRunning(CustomCTSException):
    pass


class CTSImagePullError(CustomCTSException):
    pass


class CTSTarfileDownloadError(CustomCTSException):
    pass


class CTSImageLoadErrorFromTarfile(CustomCTSException):
    pass


class CTSFTPLoginError(CustomCTSException):
    pass


class CTSInvalidImageNameError(CustomCTSException):
    pass


class CTSConfigFileError(CustomCTSException):
    pass


class CTSCannotCreateContainer(CustomCTSException):
    pass


class CTSImageNotPresent(CustomCTSException):
    pass


class CTSTarImageIOError(CustomCTSException):
    pass


class CTSUnSupportedFTPServer(CustomCTSException):
    pass


class CTSInvalidTarFileImage(CustomCTSException):
    pass


class CTSIncompleteParameters(CustomCTSException):
    pass


class CTSOutputDirectoryDoesNotExist(CustomCTSException):
    pass

class CTSDecryptionError(CustomCTSException):
    pass

class CTSPulpRepoNotFound(CustomCTSException):
    pass
