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

import logging
import re
import os
from contextlib import contextmanager
import time
from datetime import datetime

@contextmanager
def open_with_error_checking(filename, mode='r'):
    try:
        fileh = open(filename, mode)
    except IOError as err:
        yield None, err
    else:
        try:
            yield fileh, None
        finally:
            fileh.close()

def unixify_path(path):
    return path.replace('\\', '/')

def compile_patterns(patterns, ignorecase=False):
    re_pats = []
    flags = 0
    if ignorecase:
        flags |= re.IGNORECASE
    for pattern in patterns:
        pattern = '^'+re.escape(pattern)+'$'
        re_pats.append(re.compile(pattern, flags=flags))
    return re_pats

def elem_is_matched(root, elem, patterns):
    elem_mod = unixify_path(os.path.normpath(elem))
    rel_elem = get_relative_path(root, elem_mod)
    rel_elem_parts = rel_elem.split('/')
    for re_pat in patterns:
        if re.match(re_pat, rel_elem):
            return True
    return False

def split_net_drive(elem):
    m = re.match(r"^(//[^/]+)(.*)$", elem)
    if m:
        return (m.group(1), m.group(2))
    return ('', elem)

def split_win_drive(elem):
    m = re.match(r"^([a-zA-Z]:)(.*)$", elem)
    if m:
        return (m.group(1), m.group(2))
    return ('', elem)

def get_relative_path(root, elem):
    matcher = r'^'+re.escape(unixify_path(root))+r'(.*)$'
    retval = elem
    m = re.match(matcher, elem)
    if m:
        retval = m.group(1)
    if retval != '/':
        retval = retval.strip('/')
    return retval

def compare_paths_nocase(path1, path2):
    path1_lc = unixify_path(os.path.normpath(path1)).lower()
    path2_lc = unixify_path(os.path.normpath(path2)).lower()
    return path1_lc == path2_lc

def unix_time_ms(dtm=None):
    if dtm is None:
        dtm = datetime.now()
    epoch = datetime.utcfromtimestamp(0)
    return int((dtm - epoch).total_seconds() * 1000.0)

def curr_time_secs():
    return time.perf_counter()

def flush_debug_queue(q_debug, logger):
    while not q_debug.empty():
        retval = q_debug.get(True)
        log_level = retval[0]
        log_message = retval[1]
        logger.log(log_level, log_message)

def start_logging(filename, log_level, con_level):
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
    with open(fname, fmode, encoding='utf-8') as fileh:
        for line in lines:
            fileh.write('{}\n'.format(line))
