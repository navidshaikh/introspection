import os
import stat
import rpm
import json
from subprocess import Popen, PIPE
from struct import unpack

# container specific
CERT_DIR_PARENT = "/var/tmp/cert_container/"

# FILE_TYPE constants help identify file types
FTYPES = {
    "FILE_REL": 1,
    "FILE_EXEC": 2,
    "FILE_DSO": 3,
    "FILE_CORE": 4,
    "FILE_DIR": 5,
    "FILE_LINK": 6,
    "FILE_GZ": 7,
    "FILE_BZ": 8,
    "FILE_RPM": 9,
    "FILE": 0,
    }

# Package Validation Constants
PKG_VALIDATION = {"BUILD_HOST": ".redhat.com",
                  "VENDOR": "Red Hat, Inc."}

INV_FTYPES = dict([v, k] for k, v in FTYPES.iteritems())


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

    def match_bin_with_pkg(self, binary):
        """
        Match given binary to its RPM package
        """
        cmd = ["/bin/rpm", "-qf", binary]
        pkgs = Popen(cmd, stdout=PIPE).stdout.read().strip()
        if " " in pkgs:
            return None
        else:
            return pkgs.split("\n")

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

    def filetype(self, path):
        """
        filetype: reads the first few bytes from - path - and tries to
        identify the file type. At present it can identify an ELF executable,
        shared object and symbolic link files.
        """

        if not path:
            return 0

        f = os.lstat(path)
        if stat.S_ISDIR(f.st_mode):
            return FTYPES["FILE_DIR"]
        elif stat.S_ISLNK(f.st_mode):
            return FTYPES["FILE_LINK"]
        elif not stat.S_ISREG(f.st_mode):
            return 0

        try:
            f = open(path, "rb")
        except IOError:
            return 0

        s = f.read(16)
        if s[:4] == "\x7FELF":
            s = f.read(2)
            s = unpack("h", s)[0]
        elif s[:4] == "BZh9":
            s = FTYPES["FILE_BZ"]
        elif s[:4] == "\x1F\x8B\x08\x00":
            s = FTYPES["FILE_GZ"]
        elif s[:4] == "\xED\xAB\xEE\xDB":
            s = FTYPES["FILE_RPM"]
        else:
            s = FTYPES["FILE"]

        f.close()
        return s

    def get_elf_files(self, files):
        """
        Takes file list as input and returns ELF files among them as list.
        """
        elf_types = [FTYPES["FILE_REL"], FTYPES["FILE_EXEC"],
                     FTYPES["FILE_DSO"], FTYPES["FILE_CORE"]]
        return [fl for fl in files
                if os.path.exists(fl) and self.filetype(fl) in elf_types]

    def check_and_add_missing_packages(self, data):
        """
        This method compares the packages calculated using installed file with
        the total installed packages. And adds the missing packages to data.
        This will cover RPMs which do not install any library/executable,
        for eg: epel-release RPM
        """
        installed = self.get_installed_packages()
        # compare the calculated packages with installed packages
        cal_pkgs = data.keys()
        if "No-Package" in cal_pkgs:
            cal_pkgs.remove("No-Package")
        if len(installed) > len(cal_pkgs):
            # `installed` RPMs set is super-set
            missing_pkgs = list(set(installed) - set(cal_pkgs))
        else:
            missing_pkgs = []

        for pkg in missing_pkgs:
            meta = self.get_meta_of_pkg(pkg)
            info = {"FILES": self.get_installed_files(pkg),
                    "SIGNATURE": meta[0],
                    "VENDOR": meta[1],
                    "PACKAGER": meta[2],
                    "BUILD_HOST": meta[3]
                    }
            data[pkg] = info
        return data

    def get_all_data(self):
        """
        Run tests and gather all test data JSON format
        """
        data = {}
        for directory in self.bin_dirs:
            binaries = self.get_binaries_inside_directory(directory)
            for binary in binaries:
                pkgs = self.match_bin_with_pkg(binary)
                if not pkgs:
                    if "No-Package" in data:
                        data["No-Package"].append(binary)
                    else:
                        data["No-Package"] = [binary]
                else:
                    for pkg in pkgs:
                        if pkg in data:
                            data[pkg]["FILES"].append(binary)
                        else:
                            meta = self.get_meta_of_pkg(pkg)
                            info = {"FILES": [binary],
                                    "SIGNATURE": meta[0],
                                    "VENDOR": meta[1],
                                    "PACKAGER": meta[2],
                                    "BUILD_HOST": meta[3]
                                    }
                            data[pkg] = info

        data = self.check_and_add_missing_packages(data)
        return data

    def get_bins_without_pkgs(self, data):
        """
        Filter the bins present in image
        """
        if "No-Package" in data:
            if len(data["No-Package"]) > 0:
                bins = data["No-Package"]
                # changing type(data["No-Package"]) list-->dict
                datum = dict(
                    (each, INV_FTYPES[self.filetype(each)]) for each in bins)
                # Do not filter symbolic links, rather follow the real path
                datum = dict([os.path.realpath(k), v]
                             for k, v in datum.iteritems()
                             if os.path.islink(k))
                data["No-Package"] = datum
        else:
            # Value of data["No-Package"] should be a dict
            data["No-Package"] = {}
        return data

    def add_requires_of_installed_pkgs(self, data):
        """
        Add requires of installed pkgs in test data
        """
        for pkg in data.keys():
            if pkg != "No-Package":
                data[pkg].update(
                    {"REQUIRES": self.requires_of_installed_pkg(pkg)})
        return data

    def filter_non_rh_pkgs(self, data):
        """
        Filter Red Hat and Non Red Hat Packages
        """
        rht, non_rht = {}, {}
        for key, value in data.iteritems():
            if key != 'No-Package':
                if data[key]['BUILD_HOST'].endswith(PKG_VALIDATION['BUILD_HOST']):
                    rht.update({key:value})
                elif data[key]['VENDOR'] == PKG_VALIDATION['VENDOR']:
                    rht.update({key:value})
                else:
                    non_rht.update({key:value})

        return {'RedHat': rht, 'Non-RedHat': non_rht, 'No-Package': data['No-Package']}

    def run(self):
        """
        Run all of the tests
        """
        data = self.get_all_data()
        # Get requires of all installed packages

        data = self.add_requires_of_installed_pkgs(data)

        data = self.get_bins_without_pkgs(data)

        pkg_data = self.filter_non_rh_pkgs(data)

        return pkg_data


if __name__ == "__main__":
    pkg_tests = PackageTests()
    data = pkg_tests.run()

    bins_data_file_path = os.path.join(
        CERT_DIR_PARENT,
        "AdhocFiles.json")

    pkg_data_file_path = os.path.join(
        CERT_DIR_PARENT,
        "%s.json" % pkg_tests.__class__.__name__)

    with open(bins_data_file_path, "wb") as fin:
        json.dump(data["No-Package"], fin)
    data.pop('No-Package', None)
    with open(pkg_data_file_path, "wb") as fin:
        json.dump(data, fin)
