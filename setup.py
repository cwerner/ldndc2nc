#!/usr/bin/env python

import setuptools

+def version_scheme(version):
+    from setuptools_scm.version import guess_next_dev_version
+
+    version = guess_next_dev_version(version)
+    return version.replace("+", ".")


if __name__ == "__main__":
    setuptools.setup(use_scm_version={"version_scheme": version_scheme})
