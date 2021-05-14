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


def reader_process(debug_queue, cmd_queue, results_queue, shm_mode, max_block_size):
    """ This is run as a subprocess, potentially with spawn()
        be careful with vars!
    """
    pid = os.getpid()
    buf_refs = {}
    buf_names = set()
    file_obj = None
    element = ''
    bytes_read = 0
    chunk = 0
    file_size = 0
    found_eof = False
    while True:
        try:
            try:
                cqi = cmd_queue.get_nowait()
                cmd = cqi.get('cmd', None)
            except queue.Empty:
                cmd = None
            if cmd == dtutils.Cmd.INIT:
                add_buf_names = cqi.get('buf_names', [])
                element = cqi.get('element', None)
                debug_queue.put((
                    logging.DEBUG,
                    f"READER: Init {add_buf_names} for element {element}"))
                buf_names.update(add_buf_names)
                for buf_name in buf_names:
                    if shm_mode and buf_name not in buf_refs:
                        buf_refs[buf_name] = shared_memory.SharedMemory(buf_name)
                bytes_read = 0
                found_eof = False
                chunk = 0
                if element:
                    errors = None
                    file_size = os.path.getsize(element)
                    try:
                        file_obj = open(element, 'rb')
                    except IOError as err:
                        errors = err
                        debug_queue.put((
                            logging.ERROR,
                            f"READER: Problem opening \"{element}\": {err}"))
                    results_queue.put({
                        'errors': errors,
                        'element': element,
                    })
            elif cmd == dtutils.Cmd.FREE:
                add_buf_names = cqi.get('buf_names', [])
                debug_queue.put((
                    logging.DEBUG,
                    f"READER: Free {add_buf_names}"))
                buf_names.update(add_buf_names)
            elif cmd == dtutils.Cmd.QUIT:
                # for buf in buf_refs:
                #     del(buf)
                if file_obj:
                    file_obj.close()
                debug_queue.put((
                    logging.INFO,
                    "READER: Quit"))
                break
            elif cmd:
                debug_queue.put((
                    logging.WARNING,
                    'reader_process() invalid command -- pid={} cmd={}'.format(pid, cmd)))
            else:  # Steady state
                if file_obj and not file_obj.closed:
                    block_size = min(max_block_size, file_size - bytes_read)
                    if (buf_names or not shm_mode) and file_size == 0:
                        found_eof = (bytes_read == file_size)
                        results_queue.put({
                            'chunk': chunk,
                            'block_size': block_size,
                            'buf_name': None,  # Shared memory mode
                            'buf_block': b'',  # Non-shared memory mode
                            'found_eof': found_eof,
                            'mbps': 0.0,
                            'element': element,
                        })
                    while (buf_names or not shm_mode) and block_size > 0:
                        start_time = dtutils.curr_time_secs()
                        buf_block = None
                        if shm_mode:
                            buf_name = buf_names.pop()
                            debug_queue.put((
                                logging.DEBUG,
                                f"READER: Reading chunk {chunk} of {block_size} bytes into {buf_name}"))
                            buf = buf_refs[buf_name]
                            buf.buf[:block_size] = file_obj.read(block_size)
                        else:
                            buf_name = None
                            debug_queue.put((
                                logging.DEBUG,
                                f"READER: Reading chunk {chunk} of {block_size} bytes into {buf_name}"))
                            buf_block = file_obj.read(block_size)
                        bytes_read += block_size
                        found_eof = (bytes_read == file_size)
                        end_time = dtutils.curr_time_secs()
                        delta_time = end_time - start_time if end_time - start_time > 0 else 0.000001
                        mbps = block_size / 1024 / 1024 / delta_time
                        results_queue.put({
                            'chunk': chunk,
                            'block_size': block_size,
                            'buf_name': buf_name,  # Shared memory mode
                            'buf_block': buf_block,  # Non-shared memory mode
                            'found_eof': found_eof,
                            'mbps': mbps,
                            'element': element,
                        })
                        chunk += 1
                        block_size = min(max_block_size, file_size - bytes_read)
                        if not shm_mode:
                            break
                    if found_eof:  # Makes sure the file always gets closed
                        file_obj.close()
        except KeyboardInterrupt:
            break
