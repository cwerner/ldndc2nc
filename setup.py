#!/usr/bin/env python

import setuptools

def local_scheme(version):
    return ""


if __name__ == "__main__":
    setuptools.setup(use_scm_version={"version_scheme": local_scheme})
