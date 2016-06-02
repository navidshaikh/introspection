import selinux
import json


class SELinuxTests(object):
    """
    Run all selinux related tests
    """
    def is_selinux_enabled(self):
        """Selinux status
        """
        return selinux.is_selinux_enabled()

    def is_selinux_mls_enabled(self):
        """Selinux MLS status
        """
        return selinux.is_selinux_mls_enabled()

    def security_policyvers(self):
        """Selinux policy versions
        """
        return selinux.security_policyvers()

    def security_getenforce(self):
        """Selinux getenforce
        """
        if not selinux.is_selinux_enabled():
            return -1
        return selinux.security_getenforce()

    def selinux_getpolicytype(self):
        """Selinux policy type
        """
        return selinux.selinux_getpolicytype()

    def run(self, text=False, export_file=False):
        """Run few selinux checks
        """
        # is_selinux_enabled
        data = {}
        status = self.is_selinux_enabled()
        if status:
            status = "true"
        else:
            status = "false"
        data["enabled"] = status

        # security_getenforce
        mode = self.security_getenforce()
        if mode == 1:
            mode_str = "Enforcing"
        elif mode == 0:
            mode_str = "Permissive"
        elif mode == -1:
            mode_str = "Disabled"
        else:
            mode_str = "Error while checking mode"
        data["mode"] = mode_str

        # is_selinux_mls_enabled
        status = self.is_selinux_mls_enabled()
        if status:
            status = "true"
        else:
            status = "false"
        data["mls"] = status

        # security_policyvers
        if self.is_selinux_enabled():
            version = self.security_policyvers()
        else:
            version = "None"
        data["policy_version"] = version

        # selinux_getpolicytype
        policy_type = self.selinux_getpolicytype()
        if policy_type[0] == 0:
            policy_str = policy_type[1]
        else:
            policy_str = "Error while checking policy type"
        data["policy"] = policy_str

        if text:
            data = self.selinux_report_text(data)
        if export_file:
            return self._export(data, export_file)
        return data

    @staticmethod
    def selinux_report_text(json_report):
        """
        Generate text report from json report
        """
        text = "The SELinux detail for host:\n\n"
        for key, value in json_report.iteritems():
            text += "\t\t%s:\t%s\n" % (key, value)
        text += "\n"
        return text

    def _export(self, data, path):
        """
        Export data
        """
        with open(path, "wb+") as fout:
            if isinstance(data, str):
                fout.write(data)
            else:
                json.dump(data, fout)
