import os
import re
import commands
import json
import logging


class SELinuxDenials(object):
    """
    Capture SELinux denials
    """
    def _selinux_denials(self):
        """Check for SELinux denials and capture raw output from sealert
        Returns "" if no denial otherwise sealert output for denial.
        """
        alerts = []
        output = ""
        try:
            alerts = re.findall(r"^.*setroubleshoot:.*(sealert\s-l\s.*)",
                                open("/var/log/messages", "r").read(),
                                re.MULTILINE)
        except IOError, e:
            output = "IOError while recording selinux denials: %s" \
                % os.strerror(e.errno)
            return False, output

        result = []
        for alert in alerts:
            try:
                result.append({"alert": commands.getoutput(alert)})
            except Exception, err:
                # TODO: Log these errors properly
                logging.error(err)
        if result:
            return True, result
        else:
            return False, "None found"

    def run(self, export_file=None):
        """
        Run SELinux denail tests
        """
        status, data = self._selinux_denials()
        if status and export_file:
            return self._export(data, export_file)
        elif status and not export_file:
            return data
        else:
            return None

    def _export(self, data, path):
        """
        Export data in given path
        """
        with open(path, "wb+") as fout:
            json.dump(data, fout)
