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
