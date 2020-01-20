#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    'smbus2==0.2.0',
    'axp209==0.0.2',
    'psutil==5.4.5',
    'pillow==5.3.0',
    'luma.core==1.7.2',
    'luma.oled==2.4.1',
    'RPi.GPIO @ https://github.com/auto3000/RPi.GPIO_NP/archive/master.zip'
]

# No setup requirements (distutils extensions, etc.)
setup_requirements = [
]

# No test requirements
test_requirements = [
    'flake8==3.5.0',
]

setup(
    name='neo_batterylevelshutdown',
    version='0.14.0',
    description="Monitor and display battery level via the Connectbox NEO "
                "hat and gracefully shutdown when necessary",
    long_description=readme + '\n\n' + history,
    author="ConnectBox Developers",
    author_email='edwin@wordspeak.org',
    url='https://github.com/ConnectBox/neo_batterylevelshutdown',
    packages=['neo_batterylevelshutdown'],
    package_data={'neo_batterylevelshutdown': ['assets/*.png',
                                               'assets/connectbox.ttf',]},
    entry_points={
        'console_scripts': [
            'neo_batterylevelshutdown=neo_batterylevelshutdown.cli:main'
        ]
    },
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='neo_batterylevelshutdown',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
