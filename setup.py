# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Python package setup
"""

from distutils.core import setup
from setuptools import find_packages


setup(
    author='Martin Babinsky',
    author_email='martbab@gmail.com',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        ("License :: OSI Approved :: GNU Lesser General Public License v3 or "
         "later (LGPLv3+)"),
        "Topic :: Utilities",
    ],
    description='A program which builds FreeIPA and runs tests '
                'in a Docker container',
    entry_points={
        'console_scripts': [
            'ipa-docker-test-runner=ipadocker.cli:main'
        ]
    },
    install_requires=['docker-py', 'PyYAML'],
    license='GPLv3+',
    name='ipa-docker-test-runner',
    packages=find_packages(exclude=['data', 'tests']),
    package_data={
        'data': ['data/*']
    },
    version='0.2.2',
    url='https://github.com/freeipa/ipa-docker-test-runner',
)
