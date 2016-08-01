import logging
import os
import tempfile

from random import choice
from shutil import copy, rmtree
from string import ascii_lowercase
from urlparse import urlparse

import constants

from utils import ImageUtils, ContainerUtils, is_docker_running,\
    create_tarball
from inspect_tests import InspectImage, InspectContainer
from metadata import Metadata
from selinux_tests import SELinuxTests
from selinux_denials_tests import SELinuxDenials


log = logging.getLogger(os.path.basename(__file__))


class GetImage(object):

    """
    Obtain image from sources
    """

    def __init__(self, offline=False, tmpdir=None):
        self.imageutils = ImageUtils()
        self.tmpdir = tmpdir

    def image_source_type(self, image):
        return constants.LOCAL_IMAGE


class TestRunner(object):

    """
    Probe runner utility
    """

    def __init__(self, **kwargs):
        self.is_docker_daemon_running()
        self.test_dir = self._create_temp_dir()
        self.imageutils = ImageUtils()
        self.containerutils = ContainerUtils()

        self.selinux_checks = SELinuxTests()
        self.selinux_denials_test = SELinuxDenials()
        self.image_inspection_test = InspectImage()
        self.container_inspection_test = InspectContainer()
        self.metadata = Metadata()
        self._process_kwargs(**kwargs)

    def setup(self):
        """
        Setup before test run
        """
        self.getimage = GetImage(self.offline,
                                 self.test_dir)
        # This method processes the image repository and return image name with
        # tag
        self.introspection_container = self.introspection_container_name()

    def _process_kwargs(self, **kwargs):
        """
        Process the kwargs given to __init__ method
        """
        self.image = kwargs["image"]
        self.dockeruser = kwargs.get("user", None)
        self.output_dir = kwargs.get("output_dir", None)
        self.offline = kwargs.get("offline", None)

    def is_docker_daemon_running(self):
        """
        Raise if docker daemon is not running
        """
        if not is_docker_running():
            raise ctsexceptions.CTSDockerServiceNotRunning

    def introspection_container_name(self):
        """
        Returns a container name
        """
        random_name = "".join(choice(ascii_lowercase) for _ in range(6))
        return "introspection_%s" % random_name

    def is_image_tests(self):
        """
        If image tests to be ran.
        """
        return True

    def test_scripts(self):
        """
        Returns names of tests scripts
        """
        return constants.TEST_SCRIPTS_NAME

    def test_scripts_source_path(self):
        """
        Source path of tests scripts
        """
        return constants.TEST_SCRIPTS_PATH

    def test_scripts_dir_in_container(self):
        """
        Destination path of tests scripts in container
        """
        return constants.TEST_SCRIPTS_DIR_IN_CONT

    def cert_temp_parent_dir(self):
        """
        Parent directory of test dir at host
        """
        return constants.CERT_TEMP_PARENT_DIR

    def _create_temp_dir(self):
        """
        Create a temporary directory at host to be shared as volume
        """
        return tempfile.mkdtemp(dir=self.cert_temp_parent_dir())

    def introspection_shared_dir_at_host(self):
        """
        Shared directory path at host to be used as volume
        """
        return self.test_dir

    def copy_scripts_in_test_dir(self):
        """
        Copy tests scripts in cert dir at host
        """
        [copy(script, self.introspection_shared_dir_at_host())
         for script in self.test_scripts_source_path()]

    def change_perm_for_test_dir(self, test_dir, perm):
        """
        Change permission to test_dir
        """
        os.chmod(test_dir, perm)

    def pkg_report_path(self):
        """
        Package report path generated in live container test mode
        """
        return os.path.join(self.introspection_shared_dir_at_host(),
                            constants.PACKAGE_REPORT)

    def _add_user_in_params(self, user, params):
        """
        Add user in parameters
        """
        # assumes params start with "run"
        params.insert(1, "--user")
        params.insert(2, user)
        return params

    # ------------------Image-test-utilities------------------

    def _get_params_for_image_tests(self, volumes, entrypoint):
        """
        Generate parameters for image tests
        """
        # method self._add_user_in_params() asssumes params starts
        # "run", hence params should start with "run"
        params = ["run", "-v", volumes, "--entrypoint", entrypoint,
                  "--name", self.introspection_container, self.image]
        # if container needs to be run as user root
        if self.dockeruser:
            self._add_user_in_params(self.dockeruser, params)
        return params

    def _test_kickstart_path_in_container(self):
        """
        Returns entry point
        """
        return os.path.join(self.test_scripts_dir_in_container(),
                            constants.TEST_KICKSTART_SCRIPT)

    def _get_volumes_mapping(self):
        """
        Returns volumes mapping from host to container
        """
        volumes = "%s:%s:Z" % (self.introspection_shared_dir_at_host(),
                               self.test_scripts_dir_in_container())
        return volumes

    def run_image_tests(self):
        """
        Run image tests
        """
        volumes = self._get_volumes_mapping()
        log.debug("Volumes for test run %s", volumes)
        entrypoint = self._test_kickstart_path_in_container()
        params = self._get_params_for_image_tests(volumes, entrypoint)
        log.debug("Params for creating container %s", str(params))

        log.info("Creating container for running tests inside image.")
        try:
            self.containerutils.create_container(params)
        except:
            raise
        else:
            msg = "Successfully ran image tests."
            log.debug(msg)
            return self.pkg_report_path()

    # -------------------Test-run-utilities----------------------

    def pre_test_run_setup(self):
        """
        Run pre test run setup
        """
        log.debug("Copying test script in shared directory at host.")
        self.copy_scripts_in_test_dir()
        log.debug("Changing permission of shared directory at host to 0777.")
        self.change_perm_for_test_dir(self.introspection_shared_dir_at_host(), 0777)

    def _run(self):
        """
        Run all tests with clean up utility
        """
        self.run_image_tests()

        # image inspection test
        msg = "Inspecting image under test.."
        print msg
        inspect_image_report_path = os.path.join(
            self.introspection_shared_dir_at_host(),
            "%s.json" % self.image_inspection_test.__class__.__name__
        )
        self.image_inspection_test.run(
            # image=self.cert_image,
            image=self.image,
            export_file=inspect_image_report_path)

        # metadata tests
        metadata_report_path = os.path.join(
            self.introspection_shared_dir_at_host(),
            "%s.json" % self.metadata.__class__.__name__
        )
        msg = "Collecting metadata of image under test.."
        print msg
        self.metadata.run(
            # image=self.cert_image,
            image=self.image,
            export_file=metadata_report_path)

    def clean_up(self, post_run=True, during_setup=False):
        """
        Clean up after test run
        """
        msg = "Cleaning.."
        try:
            if during_setup:
                self.clean.remove_test_dir(self.test_dir)
                return
            if self.introspection_container:
                self.clean.clean_container(self.introspection_container)
            if post_run:
                if self.test_dir:
                    self.clean.remove_test_dir(self.test_dir)
                if self.image:
                    self.clean.clean_image(self.image, all_tags=True)
        except Exception as e:
            raise

    def create_testdata_tarball(self):
        """
        Create tarball of test data
        """
        log.debug("Creating tarball of test data.")
        source_dir = self.introspection_shared_dir_at_host()
        tempdir = tempfile.mkdtemp(dir=source_dir)

        files = [os.path.join(source_dir, item)
                 for item in os.listdir(source_dir)
                 if os.path.isfile(os.path.join(source_dir, item))]

        [copy(f, tempdir) for f in files]

        return create_tarball(tempdir, "container_cert", "/tmp/")

    def move_result_to_output_dir(self, result, output):
        """
        Move resultant test data from `result` to `output` directory
        data present in `result` is deleted after movement to
        `output` dir
        """
        if not os.path.isdir(output):
            raise ctsexceptions.CTSOutputDirectoryDoesNotExist(output)
        if os.path.isdir(result):
            files = [os.path.join(result, item) for item in os.listdir(result)
                     if os.path.isfile(os.path.join(result, item))]
        # if -t option is given for archiving the output, it will generate a
        # tarfile as output and thus it will be a file
        elif os.path.isfile(result):
            files = [result]
        try:
            [copy(src, output) for src in files]
        except IOError as e:
            raise
        else:
            if os.path.isfile(result):
                return os.path.join(output, os.path.basename(result))
            else:
                return output

    def remove_test_scripts_from_result(self):
        """
        Remove test scripts from result directory if any
        """
        log.debug("Removing the test scripts from shared volume.")
        for item in os.listdir(self.introspection_shared_dir_at_host()):
            if item in self.test_scripts():
                os.unlink(os.path.join(self.introspection_shared_dir_at_host(), item))

    def _post_run(self):
        """
        Operations to be performed post test run
        """
        self.remove_test_scripts_from_result()
        result = self.introspection_shared_dir_at_host()
        print result
        # if testrun data (dir/tarfile) needs to be exported in particular dir
        if self.output_dir:
            result = self.move_result_to_output_dir(result, self.output_dir)
        return result

    def run(self):
        """
        Run all tests
        """
        log.info("Start of introspecting the container.")
        self.setup()
        self.pre_test_run_setup()
        self._run()
        self._post_run()
        log.info("Completed container introspection.")
