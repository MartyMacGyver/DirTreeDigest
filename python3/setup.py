
from setuptools import setup



setup(
    name='DirTreeDigest',
    version='0.5.3',
    description='Directory Tree Digester',
    long_description = '''
A tool for generating cryptographic digests and collecting stats across a directory tree

This is an **ALPHA** development release and is not considered final

Currently works on Windows only (Linux/OSX development is ongoing)
''',
    url='https://github.com/MartyMacGyver/DirTreeDigest',
    author='Martin F. Falatic',
    author_email='martin@falatic.com',
    license='Apache License 2.0',
    packages=[
        'dirtreedigest',
    ],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
    ],
    keywords='directory digest hashing integrity filesystem checksums',
    install_requires=[],
    extras_require={},
    package_data={},
    data_files=[],
    entry_points={
        'console_scripts': [
            'dirtreedigest = dirtreedigest.main:main',
        ],
    },
)
