import json
import logging
import os
import re
import tarfile
import tempfile

from shutil import rmtree
from subprocess import Popen, PIPE
from urllib2 import HTTPError

import introexceptions

log = logging.getLogger("dockerutils")


class DockerUtils(object):

    """
    Utility via Docker CLT
    """

    def __init__(self):
        self.docker_bin = "/usr/bin/docker"

    def command(self, cmd):
        """
        Run command
        """
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        p.wait()
        out, error = p.communicate()
        return (out, error)

    def is_docker_running(self):
        """
        Check if Docker service runnin
        """
        if " docker" in self.command(["ps", "-A"])[0]:
            return True
        return False

    def docker_version(self):
        """
        Returns Docker version
        """
        cmd = [self.docker_bin, "--version"]
        return self.command(cmd)[0]

    def is_image_present(self, image):
        """
        Check if image is present locally
        """
        cmd = [self.docker_bin, "images"]
        out, _ = self.command(cmd)
        # TODO: provision for checking presence of image Id, now it checks
        # using image name
        if out.find(self.name_without_tag(image)) == -1:
            return False
        return True

    def pull_image(self, image):
        """
        Pull an image from registry
        """
        cmd = [self.docker_bin, "pull", image]
        try:
            (out, error) = self.command(cmd)
        except HTTPError:
            raise introexceptions.ImagePullError(image)
        else:
            if not self.is_image_present(image) and error != "":
                err = "Image:%s\n%s" % (image, error)
                raise introexceptions.ImagePullError(err)
            else:
                return image

    def tag_image(self, image, tag):
        """
        Tag image
        """
        cmd = [self.docker_bin, "tag", image, tag]
        self.command(cmd)

    def inspect_image(self, image):
        """
        Run inspect command on image and return output
        """
        cmd = [self.docker_bin, "inspect", image]
        return json.loads(self.command(cmd)[0])[0]

    def _remove_image(self, cmd):
        """
        Remove given image
        """
        try:
            self.command(cmd)
        except Exception:
            log.warning("Can not remove image: %s", cmd[-1])
            return False
        else:
            log.debug("Image: %s is removed.", cmd[-1])
            return True

    def remove_image(self, image):
        """
        Remove given image
        """
        if self.is_image_present(image):
            cmd = [self.docker_bin, "rmi", image]
            return self._remove_image(cmd)
        else:
            return True

    def remove_image_forcefully(self, image):
        """
        Remove given image forcefully
        """
        cmd = [self.docker_bin, "rmi", "-f", image]
        return self._remove_image(cmd)

    def is_container_present(self, container):
        """
        Check if container is present
        """
        cmd = [self.docker_bin, "ps", "-a"]
        out, error = self.command(cmd)
        if container in out:
            log.debug("Container: %s is present", container)
            return True
        else:
            log.debug("Container: %s is not present", container)
            return False

    def create_container(self, params):
        """
        Create container
        """
        params.insert(0, self.docker_bin)
        _, error = self.command(params)
        if error:
            msg = "Command used: %s\n" % params
            msg += "Error:%s" % error
            raise introexceptions.CannotCreateContainer(msg)

    def is_container_running(self, container):
        """
        Check if container is running
        """
        cmd = [self.docker_bin, "ps"]
        if " %s" % container in self.command(cmd)[0]:
            return True
        return False

    def _remove_container(self, cmd):
        """
        Remove a container using given cmd
        Returns True if container removal is successful,
        else False.
        """
        try:
            (out, error) = self.command(cmd)
        except Exception:
            msg = "Can not remove container."
            log.warning(msg)
            return False
        else:
            if out[:-1] == cmd[-1] or not self.is_container_present(cmd[-1]):
                log.debug("Container: %s is removed.", cmd[-1])
                return True
            else:
                log.debug("Container: %s is not removed.", cmd[-1])
                return False

    def remove_container(self, container):
        """
        Remove a container
        Returns True if container removal is successful,
        else False.
        """
        if self.is_container_present(container):
            cmd = [self.docker_bin, "rm", container]
            return self._remove_container(cmd)
        else:
            return True

    def remove_container_forcefully(self, container):
        """
        Remove a container forcefully
        Returns True if container removal is successful,
        else False.
        """
        if self.is_container_present(container):
            cmd = [self.docker_bin, "rm", "-f", container]
            return self._remove_container(cmd)
        else:
            return True

    def inspect_container(self, container):
        """
        Run inspect command on container
        """
        if not self.is_container_present(container):
            return {}
        cmd = [self.docker_bin, "inspect", container]
        return json.loads(self.command(cmd)[0])[0]

    def run_nsenter(self, nsenter_cmd):
        """
        Run nsenter command
        """
        self.command(nsenter_cmd)

    def pid_of_container(self, container):
        """
        Get the Process Id (pid) of container
        """
        if not self.is_container_running(container):
            return None
        return self.inspect_container(container)["State"]["Pid"]

    def name_without_tag(self, image):
        """
        Returns image name without tag
        """
        splitted_name = self.split_image_name(image)
        return "%s%s%s" % (splitted_name["url"],
                           splitted_name["repository"],
                           splitted_name["name"])

    def _raise_invalid_image_name_error(self, image):
        """
        Raise invalid image name error
        """
        raise introexceptions.InvalidImageNameError(image)

    def tag_of_image(self, t_image):
        """
        Return tag and name of image
        """
        if ":" in t_image:
            out = t_image.split(":")
            if len(out) == 2:
                name, tag = out[0], out[1]
            else:
                self._raise_invalid_image_name_error(t_image)
        else:
            name, tag = t_image, "latest"
        return {"name": name,
                "tag": tag}

    def split_image_name(self, isv_image):
        """
        Checks if ISV image name has URL or returns
        certification image name accordingly
        """
        url, repository, name, tag = "", "", "", "latest"
        if ("." in isv_image and "/" in isv_image):
            finds = [m.start() for m in re.finditer("/", isv_image)]
            # no repository / no domain name
            if len(finds) == 1:
                url = isv_image[:finds[0] + 1]
                t_image = isv_image[finds[0] + 1:]
                out = self.tag_of_image(t_image)
                repository = ""
                name, tag = out["name"], out["tag"]
            # repository/ domain name / other cases
            else:
                t_image = isv_image[finds[-1] + 1:]
                repository = isv_image[finds[-2] + 1: finds[-1] + 1]
                url = isv_image[:finds[-2] + 1]
                out = self.tag_of_image(t_image)
                name, tag = out["name"], out["tag"]
        elif "/" in isv_image:
            finds = [m.start() for m in re.finditer("/", isv_image)]
            if len(finds) == 1:
                repository = isv_image[:finds[0] + 1]
                t_image = isv_image[finds[0] + 1:]
                out = self.tag_of_image(t_image)
                name, tag = out["name"], out["tag"]
            else:
                self._raise_invalid_image_name_error(isv_image)
        else:
            url, repository = "", ""
            out = self.tag_of_image(isv_image)
            name, tag = out["name"], out["tag"]
        return {"isv_image": isv_image,
                "url": url,
                "repository": repository,
                "name":  name,
                "tag": tag,
                }

    def load_image_from_tar(self, tar_path, tmpdir=None):
        """
        Load an image from tarfile
        returns the imported image name
        """
        cmd = [self.docker_bin, "load", "-i", tar_path]
        log.debug("Loading image from tar: %s", cmd)
        try:
            out, error = self.command(cmd)
            if error:
                log.debug(error)
                raise Exception(error)
            log.info("Image is loaded from tarpath.")
        except Exception as e:
            msg = "tar/gz file: %s \n %s" % (tar_path, e)
            raise introexceptions.ImageLoadErrorFromTarfile(msg)
        else:
            return self.find_image_name_from_tar(tar_path, tmpdir)

    def extract_tarpath(self, tarpath, destpath):
        """
        Extract the tar path
        """
        try:
            tar = tarfile.open(tarpath)
            tar.extractall(path=destpath)
        except tarfile.TarError:
            msg = "Can not open the tar/gz file: %s" % tarpath
            log.error(msg)
            raise introexceptions.ImageLoadErrorFromTarfile(msg)

    def find_image_name_from_tar(self, tar_path, tmpdir=None):
        """
        Find image name given tar formatted image
        Returns: Image repository data as found from tarfile


        """
        # TODO: Check for scenario in which multiple keys are present
        # in repository metadat dict
        if tmpdir:
            temp_dir = tempfile.mkdtemp(dir=tmpdir)
        else:
            temp_dir = tempfile.mkdtemp()

        log.debug("Extracting tarfile in %s", temp_dir)

        try:
            self.extract_tarpath(tar_path, temp_dir)
            repositories = os.path.join(temp_dir, "repositories")
            with open(repositories) as fin:
                metadata = json.load(fin)
            return metadata
        except:
            msg = "tar/gz file: %s" % tar_path
            raise introexceptions.InvalidTarFileImage(msg)
        finally:
            # remove the temp dir created as tempfile does not remove it
            rmtree(temp_dir, ignore_errors=True)

    def get_all_image_long_ids(self):
        """
        This finds the all the container images long IDs
        """
        cmd = [self.docker_bin, "images", "-a", "-q", "--no-trunc"]
        try:
            out, error = self.command(cmd)
            if error:
                log.warning(error)
                raise Exception(error)
        except Exception as e:
            msg = "Could not find any images on system command failed."
            log.warning(msg)
            log.warning(e)
            return []
        else:
            return list(set(out.strip().split()))

    def get_all_images_ids_for_repository(self, repo_name):
        """
        For given repository, finds all the tags
        """
        # Remove the latest tag if present
        if repo_name.endswith(":latest"):
            repo_name = repo_name[:repo_name.find("latest")]

        log.debug("Finding all the tags ids for repository: %s", repo_name)
        cmd = [self.docker_bin, "images", "--quiet",  "--no-trunc", repo_name]
        ids = []
        log.debug(str(cmd))
        try:
            out, error = self.command(cmd)
        except Exception as e:
            msg = "Could not get the repository tags and their ids"
            log.warning(msg)
            log.warning(str(e))
            return ids
        else:
            if error:
                msg = "Could not get the repository tags and their ids"
                log.warning(msg)
                log.warning(error)
                return ids
            return list(set(out.strip().split("\n")))
