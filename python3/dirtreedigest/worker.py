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

-----------------------------------------------------
    Don't print() directly from anything in here.
-----------------------------------------------------

"""

import logging  # For constants - do not log directly from here
import os
import queue

import dirtreedigest.utils as dtutils

if dtutils.shared_memory_available():
    from multiprocessing import shared_memory  # Python 3.8+
else:
    shared_memory = None


def worker_process(debug_queue, cmd_queue, results_queue, shm_mode):
    """ This is run as a subprocess, potentially with spawn()
        be careful with vars!
    """
    pid = os.getpid()
    digest_name = 'None'
    buf_refs = {}
    while True:
        try:
            try:
                cqi = cmd_queue.get()
                cmd = cqi.get('cmd', None)
            except queue.Empty:
                cmd = None
            if cmd == dtutils.Cmd.INIT:
                digest_func = cqi.get('digest_func', None)
                if digest_func:
                    digest_instance = digest_func()
                    digest_name = digest_instance.name
                else:
                    digest_name = 'None'
                    debug_queue.put((
                        logging.ERROR,
                        'worker_process({}) init -- pid={} Missing constructor'.format(
                            digest_name, pid)))
                debug_queue.put((
                    logging.DEBUG,
                    'worker_process({}) init -- pid={}'.format(
                        digest_name, pid)))
                cmd_queue.task_done()
            elif cmd == dtutils.Cmd.PROCESS:
                block_size = cqi.get('block_size', None)
                buf_name = cqi.get('buf_name', None)
                if shm_mode:
                    if block_size > 0:
                        if buf_name not in buf_refs:
                            buf_refs[buf_name] = shared_memory.SharedMemory(buf_name)
                        buf = buf_refs[buf_name]
                        byte_block = buf.buf[:block_size]
                        debug_queue.put((
                            logging.DEBUG,
                            'worker_process() reading shared memory -- pid={} l={} c={} d={}'.format(
                                pid, block_size, byte_block[0], digest_name)))
                    else:
                        byte_block = b''
                else:
                    byte_block = cqi.get('buf_block', None)
                digest_instance.update(byte_block)
                if shm_mode:
                    del(byte_block)  # Otherwise shared_memory spews `BufferError: cannot close exported pointers exist`
                debug_queue.put((
                    logging.DEBUG,
                    'worker_process() process -- pid={} buf_name={} l={} d={}'.format(
                        pid, buf_name, block_size, digest_instance.hexdigest())))
                results_queue.put({
                    'msg': '{} processed'.format(digest_name),
                })
                cmd_queue.task_done()
            elif cmd == dtutils.Cmd.RESULT:
                debug_queue.put((
                    logging.DEBUG,
                    'worker_process({}) result -- pid={} digest={}'.format(
                        digest_name, pid, digest_instance.hexdigest())))
                results_queue.put({
                    'digest_name': digest_name,
                    'digest_value': digest_instance.hexdigest(),
                })
                cmd_queue.task_done()
            elif cmd == dtutils.Cmd.QUIT:
                # for buf in buf_refs:
                #     del(buf)
                debug_queue.put((
                    logging.DEBUG,
                    'worker_process({}) quit -- pid={}'.format(
                        digest_name, pid)))
                cmd_queue.task_done()
                break
            else:
                debug_queue.put((
                    logging.WARNING,
                    'worker_process() invalid command -- pid={} cmd={}'.format(pid, cmd)))
        except KeyboardInterrupt:
            break
