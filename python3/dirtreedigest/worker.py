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

-----------------------------------------------------
    Don't print() directly from anything in here.
-----------------------------------------------------

"""

import os
import mmap
import logging  # For constants - do not log directly from here
from enum import Enum

class WorkerSignal(Enum):
    INIT = 0
    PROCESS = 1
    RESULT = 2
    QUIT = 3

def worker_process(q_work_unit, q_results, q_debug, mmap_mode=False):
    """ This is run as a subprocess, potentially with spawn()
       be careful with vars! """
    digest_name = 'None'
    pid = os.getpid()
    while True:
        try:
            (exec_state, wu_arg1, wu_arg2) = q_work_unit.get(True)
            if exec_state == WorkerSignal.INIT:
                digest_constructor = wu_arg1
                digest_instance = digest_constructor()
                if digest_instance:
                    digest_name = digest_instance.name
                else:
                    digest_name = 'None'
                    q_debug.put((
                        logging.ERROR,
                        'worker_process({}) init -- pid={} Missing constructor'.format(
                            digest_name, pid)))
                q_debug.put((
                    logging.DEBUG,
                    'worker_process({}) init -- pid={}'.format(
                        digest_name, pid)))
                q_work_unit.task_done()
            elif exec_state == WorkerSignal.PROCESS:
                byte_block_len = wu_arg2
                if mmap_mode:
                    mm_block_name = wu_arg1
                    if byte_block_len > 0:
                        mm_block = mmap.mmap(
                            -1,
                            byte_block_len,
                            mm_block_name,
                        )
                        byte_block = mm_block.read(byte_block_len)
                        q_debug.put((
                            logging.DEBUG,
                            'worker_process() reading mmap -- pid={} l={} c={} d={} digest_instance={}'.format(
                                pid, byte_block_len, byte_block[0], digest_instance.hexdigest(), mm_block_name)))
                    else:
                        byte_block = b''
                else:
                    byte_block = wu_arg1
                digest_instance.update(byte_block)
                q_debug.put((
                    logging.DEBUG,
                    'worker_process() process -- pid={} l={} d={}'.format(
                        pid, byte_block_len, digest_instance.hexdigest())))
                q_results.put('{} processed'.format(digest_name))
                q_work_unit.task_done()
            elif exec_state == WorkerSignal.RESULT:
                q_debug.put((
                    logging.DEBUG,
                    'worker_process({}) result -- pid={} digest={}'.format(
                        digest_name, pid, digest_instance.hexdigest())))
                q_results.put((digest_name, digest_instance.hexdigest()))
                q_work_unit.task_done()
            elif exec_state == WorkerSignal.QUIT:
                q_debug.put((
                    logging.DEBUG,
                    'worker_process({}) quit -- pid={}'.format(
                        digest_name, pid)))
                q_work_unit.task_done()
                break
            else:
                q_debug.put((
                    logging.WARNING,
                    'worker_process() bad state -- pid={}'.format(pid)))
                break  # bad state
        except KeyboardInterrupt:
            break
