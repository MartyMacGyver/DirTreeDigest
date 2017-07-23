#!/usr/bin/env python3

"""

    Copyright (c) 2017 Martin F. Falatic

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

from setuptools import setup

def read_and_exec_conf(conf_file):
    conf = {}
    exec_str = ''
    with open(conf_file, 'r', encoding='utf-8') as f:
        for line in f:
            exec_str += line.rstrip('\r\n') + '\n'
        exec_str = exec_str.lstrip(u'\ufeff')
        exec(exec_str, conf)
    return conf

config = read_and_exec_conf('dirtreedigest/__config__.py')
pkg_info = config['pkg_data']

setup(
    name=pkg_info['name'],
    version=pkg_info['version'],
    description=pkg_info['description'],
    long_description=pkg_info['long_description'],
    url=pkg_info['url'],
    author=pkg_info['author'],
    author_email=pkg_info['author_email'],
    license=pkg_info['license'],
    classifiers=pkg_info['classifiers'],
    keywords=pkg_info['keywords'],
    packages=pkg_info['packages'],
    entry_points=pkg_info['entry_points'],
    install_requires=pkg_info['install_requires'],
    extras_require=pkg_info['extras_require'],
    package_data=pkg_info['package_data'],
    data_files=pkg_info['data_files'],
)
