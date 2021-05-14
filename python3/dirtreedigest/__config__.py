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

import logging

PACKAGE_DATA = {
    'name': 'DirTreeDigest',
    'version': '1.0.6',
    'url': 'https://github.com/MartyMacGyver/DirTreeDigest',
    'author': 'Martin F. Falatic',
    'author_email': 'martin@falatic.com',
    'copyright': 'Copyright (c) 2017-2021',
    'license': 'Apache License 2.0',
    'description': 'Directory Tree Digester and Comparator',
    'long_description': """
A suite for digesting and analyzing filesystems:

dirtreedigest - generates cryptographic digests and collects stats across a directory tree

dirtreecmp - compare two dirtreedigest reports

This is a development release and is not considered final

For Windows, OS X and Linux
    """,
    'keywords': 'directory digest hashing integrity filesystem checksums',
    'classifiers': [
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Development Status :: 5 - Production/Stable',
    ],
    'packages': [
        'dirtreedigest',
    ],
    'entry_points': {
        'console_scripts': [
            'dirtreedigest=dirtreedigest.main_digest:main',
            'dirtreecmp=dirtreedigest.main_compare:main',
        ],
    },
    'install_requires': [],
    'extras_require': {},
    'package_data': {},
    'data_files': [],
}

CONTROL_DATA = {
    'logfile_level': logging.INFO,
    'console_level': logging.INFO,
    'outfile_prefix': 'dtdigest',
    'outfile_ext': 'thd',
    'outfile_name': None,
    'altfile_name': None,
    'logfile_ext': 'log',
    'shm_mode': True,
    'max_concurrent_jobs': 32,
    'max_buffers': 4,
    'max_block_size_mb': 16,
    'max_block_size': None,
    'ignore_path_case': False,
    'ignored_files': None,
    'ignored_dirs': None,
    'counts': {
        'files': 0,
        'dirs': 0,
        'ignored': 0,
        'errors': 0,
        'bytes_read': 0,
    },
    'altfile_digest': None,
    'buffer_blocks': None,
    'buffer_names': None,
    'buffer_sizes': None,
    'default_digests': None,
    'selected_digests': [],
    'reader_proc': None,
    'reader_cmd_queue': None,
    'reader_results_queue': None,
    'worker_procs': None,
    'worker_cmd_queues': None,
    'worker_results_queue': None,
    'debug_queue': None,
    'root_dir': None,
}

CONTROL_DATA['default_digests'] = [
    # 'noop',
    # 'crc32',
    # 'adler32',
    'md5',
    'sha1',
    # 'sha224',
    'sha256',
    # 'sha384',
    # 'sha512',
    # 'blake2b',
    # 'blake2s',
    # 'sha3_224',
    # 'sha3_256',
    # 'sha3_384',
    # 'sha3_512',
    # 'shake_128',
    # 'shake_256',
    # 'foo',
    # 'sha1',
    # 'noop1',
    # 'noop2',
    # 'noop3',
    # 'noop4',
    # 'noop5',
    # 'noop6',
    # 'noop7',
    # 'noop8',
]

CONTROL_DATA['ignored_files'] = [
    'pagefile.sys',
    'hiberfil.sys',
]

CONTROL_DATA['ignored_dirs'] = [
    'Config.Msi',
    '$RECYCLE.BIN',
    'Recycled',
    'Recycler',
    'System Volume Information',
    'Temp',
    'msdownld.tmp',
]
