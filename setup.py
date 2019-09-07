#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0111,W6005,W6100
from __future__ import absolute_import, print_function

import os
import re
import sys

from setuptools import setup


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


VERSION = get_version('unlockerx', '__init__.py')

if sys.argv[-1] == 'tag':
    print("Tagging the version on github:")
    os.system("git tag -a %s -m 'version %s'" % (VERSION, VERSION))
    os.system("git push --tags")
    sys.exit()

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
CHANGELOG = open(os.path.join(os.path.dirname(__file__), 'CHANGELOG.rst')).read()

setup(
    name='unlockerx',
    version=VERSION,
    description="""An app to manage (and remove) password and IP-based locks.""",
    long_description=README + '\n\n' + CHANGELOG,
    author='Omar Al-Ithawi',
    author_email='omar@appsembler.com',
    url='https://github.com/appsembler/unlockerX',
    packages=[
        'unlockerx',
    ],
    include_package_data=True,
    install_requires=[
        "Django>=1.8,<2.1", "django-model-utils>=2.0"
    ],
    license="MIT License",
    zip_safe=False,
    keywords='Django Appsembler Open edX Platform',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    entry_points={
        "lms.djangoapp": [
            "unlockerx = unlockerx.apps:UnlockerXConfig",
        ],
        "cms.djangoapp": [
            "unlockerx = unlockerx.apps:UnlockerXConfig",
        ],
    },
)
