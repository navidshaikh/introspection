# Copyright 2014 Red Hat Inc.
# Navid Shaikh <nshaikh@redhat.com>
#
# This program is a free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the license, or(at your option) any
# later version. See http://www.gnu.org/copyleft/gpl.html for the full text of
# the license.
#

import os
import json
import re

from subprocess import Popen, PIPE

# container specific
CERT_DIR_PARENT = "/var/tmp/container_introspection/"


class RPMVerifyTest(object):
    """
    Verify installed RPMs
    """
    def get_command(self):
        """
        Command to run the rpm verify test
        """
        return ["/bin/rpm", "-Va"]

    def run_command(self, cmd):
        """
        Run command for rpm verify test
        """
        out, error = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
        return (out, error)

    def get_meta_of_rpm(self, rpm):
        """
        Get metadata of given installed package.
        Metadata captured: SIGPGP, VENDOR, PACKAGER, BUILDHOST
        """
        qf = "%{SIGPGP:pgpsig}|%{VENDOR}|%{PACKAGER}|%{BUILDHOST}"
        cmd = ["/bin/rpm", "-q", "--qf", qf, rpm]
        out, _ = self.run_command(cmd)
        out = out.split("|")
        return {"RPM": rpm,
                "SIGNATURE": out[0],
                "VENDOR": out[1],
                "PACKAGER": out[2],
                "BUILDHOST": out[3]
                }

    def source_rpm_of_file(self, filepath):
        """
        Find source RPM of given filepath
        """
        cmd = ["/bin/rpm", "-qf", filepath]
        out, _ = self.run_command(cmd)
        if " " in out:
            return ""
        else:
            return out.split("\n")[0]

    def process_cmd_output_data(self, data):
        """
        Process the command output data
        """
        lines = data.split("\n")[:-1]
        result = []
        for line in lines:
            line = line.strip()
            if line.startswith("error:"):
                continue
            match = re.search(r'^([0-9A-Za-z.]+)\s+([c]{0,1})\s+(\W.*)$', line)
            if match is None:
              return "error"

            if match.groups()[1] == 'c':
                continue

            filepath = match.groups()[2]
            rpm = self.source_rpm_of_file(filepath)
            rpm_meta = self.get_meta_of_rpm(rpm)
            # do not include the config files in the result


            result.append({
              "issue": match.groups()[0],
              "config": match.groups()[1] == 'c',
              "filename" : match.groups()[2],
              "rpm": self.get_meta_of_rpm(rpm)})
        return result

    def _run(self):
        """
        Run the RPM verify test
        """
        cmd = self.get_command()
        out, error = self.run_command(cmd)
        result = []
        result = self.process_cmd_output_data(out)
        # TODO: since this script is running inside container while we have the
        # logging on host, we should find a better way to log this message back
        # Also we should log the RPMs failing the rpm -V test
        #print "Issue found while running rpm -Va test: "
        #print error
        return {"rpmVa_issues": result}

    def run(self, output_file=None):
        """
        Run the RPM Verify test and export report if required
        """
        result = self._run()
        if output_file:
            self.export_report(result, output_file)

    def export_report(self, data, output_file):
        """
        Export the JSON data in output_file
        """
        with open(output_file, "wb+") as fin:
            json.dump(data, fin)


if __name__ == "__main__":
    rpmva_tests = RPMVerifyTest()

    data_file_path = os.path.join(CERT_DIR_PARENT,
                                  "%s.json" % rpmva_tests.__class__.__name__)
    data = rpmva_tests.run(output_file=data_file_path)
