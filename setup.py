#!/usr/bin/env python

import setuptools

# overwrite default behavior since test pypi does now allow dirty version numbering
def local_scheme(version):
    return ""


if __name__ == "__main__":
    setuptools.setup(use_scm_version={"local_scheme": local_scheme})
