import json
import os

PROBE_CONFIG = "introspection_execution_errors.json"

try:
    PROBE_ERRORS = json.load(
        open(os.path.join("/etc/introspection/", PROBE_CONFIG)))
except IOError:
    filename = os.path.join(os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))),
                            "etc/introspection/",
                            PROBE_CONFIG)
    PROBE_ERRORS = json.load(open(filename))


class IntroExceptions(Exception):
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


class DockerServiceNotRunning(IntroExceptions):
    pass


class ImagePullError(IntroExceptions):
    pass


class TarfileDownloadError(IntroExceptions):
    pass


class ImageLoadErrorFromTarfile(IntroExceptions):
    pass


class InvalidImageNameError(IntroExceptions):
    pass


class ConfigFileError(IntroExceptions):
    pass


class CannotCreateContainer(IntroExceptions):
    pass


class ImageNotPresent(IntroExceptions):
    pass


class TarImageIOError(IntroExceptions):
    pass


class InvalidTarFileImage(IntroExceptions):
    pass


class OutputDirectoryDoesNotExist(IntroExceptions):
    pass
