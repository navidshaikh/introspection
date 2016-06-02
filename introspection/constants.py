import os
from os import path

PACKAGE_TESTS = "package_tests.py"
RPM_VERIFY_TESTS = "rpm_verify_tests.py"
ELF_TESTS = "elf_tests.py"
SHELL_SCRIPT = "introspection_script.sh"
LOGFILE_PATH = "/var/tmp/introspection.log"

TEST_SCRIPTS_NAME = [
    SHELL_SCRIPT,
#    PACKAGE_TESTS,
#    RPM_VERIFY_TESTS,
#     ELF_TESTS,
]

if path.exists(path.join("usr/bin", SHELL_SCRIPT)):
    # local git repository
    SHELL_SCRIPT_PATH = path.join("usr/bin", SHELL_SCRIPT)
else:
    # after installation
    SHELL_SCRIPT_PATH = path.join("/usr/bin/", SHELL_SCRIPT)

TEST_SCRIPTS_PATH = [
    SHELL_SCRIPT_PATH,
#     path.join(path.dirname(__file__), PACKAGE_TESTS),
#    path.join(path.dirname(__file__), ELF_TESTS),
#    path.join(path.dirname(__file__), RPM_VERIFY_TESTS),
]



TEST_KICKSTART_SCRIPT = "introspection_script.sh"

TEST_SCRIPTS_DIR_IN_CONT = "/var/tmp/container_introspection/"
CERT_TEMP_PARENT_DIR = "/tmp/"

REPORT_DIR = "/var/tmp/introspection_report/"

INVALID_IMAGE = 0
LOCAL_IMAGE = 1
REGISTRY_IMAGE = 2
TARFILE_IMAGE = 3
FTP_TARFILE_IMAGE = 4
LOCAL_IMAGE_WITH_REGISTRY_NAME = 5
FTP_GZFILE_IMAGE = 6
GZFILE_IMAGE = 7

PACKAGE_REPORT = "PackageTests.json"
