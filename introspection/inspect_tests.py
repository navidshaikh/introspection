import json

from dockerutils import DockerUtils


class InspectImage(object):
    """
    Inspect test for image
    """
    def __init__(self):
        self.docker = DockerUtils()

    def inspect_image(self, image):
        """
        Inspect given image
        """
        return self.docker.inspect_image(image)

    @staticmethod
    def inspect_image_report_text(json_data):
        """
        Generate text from inspect_image json response
        """
        text = "Image inspection:\n"
        for key, value in json_data.iteritems():
            if isinstance(value, dict):
                text += "\t%s:\n" % key
                for k, v in json_data[key].iteritems():
                    text += "\t\t- %s: %s\n" % (k, str(v))
            else:
                text += "\t%s:\t%s\n" % (key, str(value))
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

    def run(self, image, text=False, export_file=None):
        """
        Run image inspection tests
        """
        data = self.inspect_image(image)
        if text:
            data = self.inspect_image_report_text(data)
        if export_file:
            return self._export(data, export_file)
        return data


class InspectContainer(object):
    """
    Inspect test for container
    """
    def __init__(self):
        self.docker = DockerUtils()

    def inspect_container(self, container):
        """
        Inspect given container
        """
        return self.docker.inspect_container(container)

    @staticmethod
    def inspect_container_report_text(json_data):
        """
        Generate text from inspect_container json response
        """
        text = "Container inspection:\n"
        for key, value in json_data.iteritems():
            if isinstance(value, dict):
                text += "\t%s:\n" % key
                for k, v in json_data[key].iteritems():
                    text += "\t\t- %s: %s\n" % (k, str(v))
            else:
                text += "\t%s:\t%s\n" % (key, str(value))
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

    def run(self, container, text=False, export_file=None):
        """
        Run container inspection tests
        """
        data = self.inspect_container(container)
        if text:
            data = self.inspect_container_report_text(data)
        if export_file:
            return self._export(data, export_file)
        return data
