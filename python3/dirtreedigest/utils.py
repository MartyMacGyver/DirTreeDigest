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
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from enum import Enum


# Enums to communicate with subprocesses
Cmd = Enum('Cmd', 'INIT PROCESS FREE RESULT QUIT')


def shared_memory_available():
    """ Single place to check (handy if it gets backported) """
    return sys.version_info >= (3, 8)


@contextmanager
def open_with_error_checking(filename, mode='r'):
    """ Open a file for reading with error checking """
    try:
        fileh = open(filename, mode)
    except IOError as err:
        yield None, err
    else:
        try:
            yield fileh, None
        finally:
            fileh.close()


def datetime_as_str(dtm=None):
    if not dtm:
        dtm = datetime.now()
    return "{:%Y%m%d_%H%M%S}".format(dtm)


def unixify_path(path):
    """ Convert path to Unix format """
    return path.replace('\\', '/')


def compile_patterns(patterns, ignorecase=False):
    """ Compile exclusion patterns to regular expressions """
    re_pats = []
    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    for pattern in patterns:
        pattern = '^' + re.escape(pattern) + '$'
        re_pats.append(re.compile(pattern, flags=flags))
    return re_pats


def elem_is_matched(root, elem, patterns):
    """ Check if element matches any of the exclusion patterns """
    elem_mod = unixify_path(os.path.normpath(elem))
    rel_elem = get_relative_path(root, elem_mod)
    for re_pat in patterns:
        if re.match(re_pat, rel_elem):
            return True
    return False


def split_net_drive(elem):
    """ For network shares, split network and path parts """
    mval = re.match(r"^(//[^/]+)(.*)$", elem)
    if mval:
        return (mval.group(1), mval.group(2))
    return ('', elem)


def split_win_drive(elem):
    """ For Windows drives, split drive spec and path parts """
    mval = re.match(r"^([a-zA-Z]:)(.*)$", elem)
    if mval:
        return (mval.group(1), mval.group(2))
    return ('', elem)


def get_relative_path(root, elem):
    """ Get the element path relative to a given root path """
    matcher = r'^' + re.escape(unixify_path(root)) + r'(.*)$'
    retval = elem
    mval = re.match(matcher, elem)
    if mval:
        retval = mval.group(1)
    if retval != '/':
        retval = retval.strip('/')
    return retval


def compare_paths(path1, path2, ignorecase=False):
    """ Compare two paths """
    path1_mod = unixify_path(os.path.normpath(path1))
    path2_mod = unixify_path(os.path.normpath(path2))
    if ignorecase:
        path1_mod = path1_mod.lower()
        path2_mod = path2_mod.lower()
    return path1_mod == path2_mod


def unix_time_ms(dtm=None):
    """ Get Unix time in msec """
    if dtm is None:
        dtm = datetime.now()
    epoch = datetime.utcfromtimestamp(0)
    return int((dtm - epoch).total_seconds() * 1000.0)


def curr_time_secs():
    """ Get current high-resolution time """
    return time.perf_counter()


def flush_debug_queue(debug_queue, logger):
    """ Flush the debug message queue """
    while not debug_queue.empty():
        retval = debug_queue.get()
        log_level = retval[0]
        log_message = retval[1]
        logger.log(log_level, log_message)


def start_logging(filename, log_level, con_level):
    """ Initialize file and console logs """
    logfile_handler = logging.FileHandler(filename, 'w', 'utf-8')
    log_fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    logfile_handler.setFormatter(log_fmt)
    logfile_handler.setLevel(log_level)
    console_handler = logging.StreamHandler()
    con_fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console_handler.setFormatter(con_fmt)
    console_handler.setLevel(con_level)
    logging.basicConfig(
        level=logging.NOTSET,  # This must be set to something
        handlers=[logfile_handler, console_handler])


def outfile_write(fname, fmode, lines):
    """ Write a block of data to the output file """
    with open(fname, fmode, encoding='utf-8') as fileh:
        for line in lines:
            fileh.write('{}\n'.format(line))
