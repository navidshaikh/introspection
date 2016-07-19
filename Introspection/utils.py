import os
import time
import logging
import tarfile
import base64
from subprocess import Popen, PIPE

from dockerutils import DockerUtils
from constants import LOGFILE_PATH


def command(cmd):
    """
    Run command
    """
    out, error = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    return (out, error)


def configure_logging():
    """
    Configure logging
    """
    fmt = "[%(asctime)s] %(name)s - %(filename)s - %(levelname)s - %(message)s"
    logging.basicConfig(filename=LOGFILE_PATH,
                        level=logging.DEBUG,
                        format=fmt)


def is_docker_running():
    """
    Check if Docker daemon is running or not
    """
    docker = DockerUtils()
    return docker.is_docker_running()


def docker_version():
    """
    Get the docker version
    """
    docker = DockerUtils()
    return docker.docker_version()


def create_tarball(source, tarname, tarpath):
    """
    Create tarball
   :arg source: Source directory where files are present
   :arg tarname: Name of the tarball
   :arg tarpath: Path to the directory to create the tarball
   :return: Path to the newly created log file
   """

    rel = time.strftime("%d%b%Y_%H%M%S_%s", time.localtime())
    tarball = os.path.join(
        tarpath, ("%s-%s.tar.bz2" % (tarname, rel))
    )
    tar = tarfile.open(tarball, "w:bz2")
    for dirname, _, filenames in os.walk(source):
        for filename in filenames:
            if filename.endswith(".json"):
                tar.add(os.path.join(dirname, filename))
    tar.close()
    return tar.name


def decode_base64(base64_input, output_path):
    """
    Decodes a bunch of base64 encoded data and writes it
    into a file at output_path.
    """

    try:
        decoded_file_path = open(output_path, 'w')
        decoded_file_path.write(base64.b64decode(base64_input))
    except TypeError:
        log.error('Could not decode base64 dockerfile.')
    except IOError:
        log.error('Could not open write dockerfile to file.')


class ImageUtils(object):

    """
    Image related utilities
    """

    def __init__(self):
        self.docker = DockerUtils()

    def is_image_present_locally(self, image):
        """
        Check if image is present locally
        """
        return self.docker.is_image_present(image)

    def tag_image(self, image, tag):
        """
        Tag image
        """
        return self.docker.tag_image(image, tag)

    def pull_image_from_registry(self, image):
        """
        Pull given image from registry
        """
        return self.docker.pull_image(image)

    def is_tar_file_image(self, image):
        """
        Check image is tar file image
        """
        # TODO: Better approach to find image type
        if image.endswith(".tar"):
            return True
        return False

    def is_docker_image(self, image):
        """
        Check if image is docker image
        """
        # TODO: Better approach to find image type
        if not image.endswith(".tar"):
            return True
        return False

    def is_registry_image(self, image):
        """
        Check if image have registry name
        """
        splitted_image_name = self.split_image_name(image)
        if splitted_image_name["url"]:
            return True

    def split_image_name(self, image):
        """
        Split image name into its components
        """
        return self.docker.split_image_name(image)

    def remove_image(self, image):
        """
        Remove image
        """
        return self.docker.remove_image(image)

    def remove_image_forcefully(self, image):
        """
        Remove image forcefully
        """
        return self.docker.remove_image_forcefully(image)

    def load_image_from_tar(self, tar_image, tmpdir=None):
        """
        Load image from tar file of image
        """
        return self.docker.load_image_from_tar(tar_image, tmpdir)

    def get_all_images_ids_for_repository(self, repository_name):
        """
        Get all the image:tag ids for given repository name
        """
        return self.docker.get_all_images_ids_for_repository(
            repository_name)


class ContainerUtils(object):

    """
    Container related operations aggregated in single class
    """

    def __init__(self, container=None):
        self.docker = DockerUtils()

    def create_container(self, params):
        """
        Create container
        """
        return self.docker.create_container(params)

    def is_container_present(self, container):
        """
        Check if container is present
        """
        return self.docker.is_container_present(container)

    def remove_container(self, container):
        """
        Remove given container
        """
        return self.docker.remove_container(container)

    def remove_container_forcefully(self, container):
        """
        Remove a container forcefully
        Returns True if container removal is successful,
        else False.
        """
        return self.docker.remove_container_forcefully(container)

    def attach_via_nsenter(self, nsenter_cmd):
        """
        Attach to container via nsenter
        """
        return self.docker.run_nsenter(nsenter_cmd)

    def pid_of_container(self, container):
        """
        Get process id of running container
        """
        return self.docker.pid_of_container(container)
