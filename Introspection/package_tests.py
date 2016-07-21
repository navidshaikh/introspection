import os
import stat
import rpm
import json
from subprocess import Popen, PIPE
from struct import unpack

# container specific
SHARED_DIR_PARENT = "/var/tmp/container_introspection/"


class PackageTests(object):
    """
    Package tests for container
    """
    def __init__(self):
        self.bin_dirs = self.binaries_directories()

    def split_rpm_nvra(self, name):
        """
        split_rpm_nvra: splits the given rpm NVRA into a dictionary of fields
        like; name, version, release, epoch, and architecture.
        """
        if not name:
            return None

        rfields = {}

        n = name.rfind(".")
        rfields["ARCH"] = name[n + 1:]
        name = name[:n]         # strip off "i386/i686/x86_64/.src" part

        n = name.rfind("-")
        rfields["RELEASE"] = name[n + 1:]
        name = name[:n]         # strip off rpm release

        n = name.rfind("-")
        rfields["VERSION"] = name[n + 1:]
        name = name[:n]         # strip off rpm version

        epoch = None
        n = name.find(":")
        if (n >= 0):
            epoch = name[:n]
        rfields["EPOCH"] = epoch

        rfields["NAME"] = name[n + 1:]

        return rfields

    def binaries_directories(self):
        """
        Return all directories path where binaries present
        """
        dirs = ["/bin",
                "/usr/bin",
                "/usr/local/bin",
                "/sbin",
                "/usr/sbin",
                "/usr/local/sbin",
                "/lib",
                "/lib64",
                "/usr/lib",
                "/usr/lib64",
                "/usr/local/lib",
                "/usr/local/lib64",
                "/usr/libexec",
                "/usr/local/libexec",
                "/opt",
                "/usr/opt",
                "/usr/local/opt",
                ]

        # extend with the paths in the PATH variable
        dirs.extend(os.environ["PATH"].split(":"))
        if "LD_LIBRARY_PATH" in os.environ:
            # also include user-defined LD Paths
            dirs.extend(os.environ["LD_LIBRARY_PATH"].split(":"))
        return list(set(dirs))

    def get_binaries_inside_directory(self, directory):
        """
        Get all binaries present inside given directory,
        find all binaries present in subdirectories as well.
        """
        files = []
        for dirpath, dirname, filenames in os.walk(directory, topdown=False):
            for fn in filenames:
                files.append(os.path.join(dirpath, fn))
        return files

    def get_installed_packages(self):
        """
        Get all installed packages in system
        """
        ts = rpm.TransactionSet()
        mi = ts.dbMatch()
        return [hdr[rpm.RPMTAG_NVRA] for hdr in mi]

    def get_installed_files(self, pkg):
        """
        Get all installed files by given installed rpm
        """
        rpm_name = self.split_rpm_nvra(pkg)["NAME"]
        ts = rpm.TransactionSet()
        for hdr in ts.dbMatch("name", rpm_name):
            return hdr[rpm.RPMTAG_FILENAMES]

    def get_signature_of_give_package(self, pkg):
        """
        Get GPG key of given installed pkg
        """
        cmd = ["/bin/rpm", "-q", "--qf", "%{SIGPGP:pgpsig}", pkg]
        return Popen(cmd, stdout=PIPE).stdout.read().strip()

    def get_meta_of_pkg(self, pkg):
        """
        Get metadata of given installed package.
        Metadata captured: SIGPGP, VENDOR, PACKAGER, BUILDHOST
        """
        qf = "%{SIGPGP:pgpsig}|%{VENDOR}|%{PACKAGER}|%{BUILDHOST}"
        cmd = ["/bin/rpm", "-q", "--qf", qf, pkg]
        return Popen(cmd, stdout=PIPE).stdout.read().split("|")

    def requires_of_installed_pkg(self, pkg):
        """
        Obtain requires of installed_package
        """
        cmd = ["/bin/rpm", "-q", "--requires", pkg]
        out = Popen(cmd, stdout=PIPE).stdout.read()
        return list(set(out.split("\n")[:-1]))

    def get_all_binaries_libs(self):
        """
        Run the list of all libraries and binaries in standard
        path of a linux system along with paths added LD_LIBRARY_PATH
        """
        bins = []
        for directory in self.bin_dirs:
            bins += self.get_binaries_inside_directory(directory)
        return bins

    def find_adhoc_bins_libs(self, installed_packages=[]):
        """
        Diffs the libraries and binaries present in standard path
        along with paths in the LD_LIBRARY_PATH to the installed files
        via RPMs and returns the files which are not installed in system
        via RPM packages
        """
        bins = self.get_all_binaries_libs()
        if not installed_packages:
            installed_packages = self.get_installed_packages()
        for package in installed_packages:
            # removes the files from all `bins` variable which are
            # installed by RPM
            print len(bins)
            bins = list(set(bins) - set(self.get_installed_files(package)))
            print len(bins)

        return bins

    def run(self):
        """
        Run tests and gather all test data JSON format
        """
        installed_packages = self.get_installed_packages()
        installed_packages_data = {}
        for package in installed_packages:
            metadata = self.get_meta_of_pkg(package)
            info = {"SIGNATURE": metadata[0],
                    "VENDOR": metadata[1],
                    "PACKAGER": metadata[2],
                    "BUILD_HOST": metadata[3],
                    "REQUIRES": self.requires_of_installed_pkg(package)
                    }
            installed_packages_data[package] = info

        return {"Installed_Packages": installed_packages_data,
                "Adhoc_bins_libs": self.find_adhoc_bins_libs(
                    installed_packages)
                }


if __name__ == "__main__":
    pkg_tests = PackageTests()
    data = pkg_tests.run()

    bins_data_file_path = os.path.join(
        SHARED_DIR_PARENT,
        "AdhocFiles.json")

    pkg_data_file_path = os.path.join(
        SHARED_DIR_PARENT,
        "%s.json" % pkg_tests.__class__.__name__)

    with open(bins_data_file_path, "wb") as fin:
        json.dump(data["Adhoc_bins_libs"], fin)
    data.pop("Adhoc_bins_libs", None)
    with open(pkg_data_file_path, "wb") as fin:
        json.dump(data, fin)
