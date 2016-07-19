#!/usr/bin/python
#

from distutils.core import setup

setup(
    name="introspection",
    version="0.1",
    description="""
Tooling to introspect container images detailing the
contents and ABI properties.""",
    platforms=["Linux"],
    author=["Navid Shaikh"],
    author_email=["nshaikh@redhat.com"],
    url="http://www.redhat.com",
    license="http://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
    scripts=[
        "introspect",
        "introspection_script.sh"],
    packages=["Introspection"],
    data_files=[
        ("/etc/Introspection",
         ["etc/Introspection/introspection_execution_errors.json"]),
    ],
)
