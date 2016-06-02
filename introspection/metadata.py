import json

from utils import docker_version
from inspect_tests import InspectImage


class Metadata(object):
    """
    Collect metadata about the image under test and test run
    """
    def __init__(self):
        self.inspect_image = InspectImage()
        # later set by another method
        self.number_of_layers = 1

    def _image_inspection(self, image, inspection=None):
        """
        Check if inspection is present else, find inspection of given image
        """
        if not inspection and image:
            inspection = self.inspect_image.run(image)
        return inspection

    def docker_version_of_test_run_host(self):
        """
        Find version of docker installed on host where are tests are ran.
        """
        return docker_version()

    def docker_version_of_image_build_host(self, inspection):
        """
        Find version of docker where image is built
        """
        return inspection.get("DockerVersion",
                              inspection.get("docker_version", ""))

    def image_id(self, inspection):
        """
        Find id of image in inspection data
        """
        return inspection.get("Id", inspection.get("id", ""))

    def parent_image_id(self, inspection):
        """
        Find parent image id of give image/inspection
        """
        return inspection.get("Parent", inspection.get("parent", ""))

    def image_author(self, inspection):
        """
        Find maintainer of image under test
        """
        return inspection.get("Author", inspection.get("author", ""))

    def image_created(self, inspection):
        """
        Find the timestamp when image layer was created
        """
        return inspection.get("Created", inspection.get("created", ""))

    def image_comment(self, inspection):
        """
        Find the comments present in image
        """
        return inspection.get("Comment", inspection.get("comment", ""))

    def collect_meta_of_layer(self, inspection):
        """
        Collect multiple attributes from inspection of layers
        """
        return {"Id": self.image_id(inspection),
                "Parent_Id": self.parent_image_id(inspection),
                "Author": self.image_author(inspection),
                "DockerVersion": self.docker_version_of_image_build_host(
                    inspection),
                "Created": self.image_created(inspection),
                "Comments": self.image_comment(inspection),
                }

    def find_all_layers(self, layered_image):
        """
        Find all layers of given image
        and return the metadata of each layer
        """
        data, counter, base = {}, 0, False
        while not base:
            inspection = self._image_inspection(image=layered_image)
            counter += 1
            data[counter] = self.collect_meta_of_layer(inspection)
            parent_id = self.parent_image_id(inspection)
            if not parent_id:
                base = True
                continue
            else:
                # now trace back for parent detail
                layered_image = parent_id

        self.number_of_layers = counter
        return data

    def base_image_of_layered_image(self, all_layers):
        """
        Find the base image of given layered image
        """
        layer_nos = all_layers.keys()
        return all_layers[max(layer_nos)]

    def top_layer_of_layered_image(self, all_layers):
        """
        Find the top layer of give layered image
        """
        layer_nos = all_layers.keys()
        return all_layers[min(layer_nos)]

    def _run(self, image):
        """
        Run the image metadata test and return data in JSON format
        """
        all_layers = self.find_all_layers(image)
        return {"image_under_test": image,
                "number_of_layers": self.number_of_layers,
                "top_layer": self.top_layer_of_layered_image(all_layers),
                "base_image": self.base_image_of_layered_image(all_layers),
                "all_layers": all_layers,
                "DockerVersion_of_test_run_host":
                self.docker_version_of_test_run_host(),
                }

    def export(self, data, filepath):
        """
        Export the report
        """
        with open(filepath, "wb+") as fin:
            json.dump(data, fin)

    def run(self, image, export_file=None):
        """
        Run the test and export the data
        """
        data = self._run(image)
        if export_file:
            return self.export(data, export_file)
        else:
            return data
