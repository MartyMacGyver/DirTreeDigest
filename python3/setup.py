#!/usr/bin/env python3

"""

    Copyright (c) 2017-2021 Martin F. Falatic

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
package_data = config['PACKAGE_DATA']

setup(
    name=package_data['name'],
    version=package_data['version'],
    description=package_data['description'],
    long_description=package_data['long_description'],
    url=package_data['url'],
    author=package_data['author'],
    author_email=package_data['author_email'],
    license=package_data['license'],
    classifiers=package_data['classifiers'],
    keywords=package_data['keywords'],
    packages=package_data['packages'],
    entry_points=package_data['entry_points'],
    install_requires=package_data['install_requires'],
    extras_require=package_data['extras_require'],
    package_data=package_data['package_data'],
    data_files=package_data['data_files'],
)
