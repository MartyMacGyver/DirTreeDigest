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

import ctypes
import logging
import multiprocessing
import os
import stat
import sys

import dirtreedigest.digester as dtdigester
import dirtreedigest.reader as dtreader
import dirtreedigest.utils as dtutils
import dirtreedigest.worker as dtworker

if dtutils.shared_memory_available():
    from multiprocessing import shared_memory  # Python 3.8+
else:
    shared_memory = None


# pylint: disable=bad-whitespace
class Walker(object):
    """ Directory walker and supporting functions """

    # Windows file attributes
    FILE_ATTRIBUTE_NONE                = 0x00000  # noqa: E221
    FILE_ATTRIBUTE_READONLY            = 0x00001  # noqa: E221
    FILE_ATTRIBUTE_HIDDEN              = 0x00002  # noqa: E221
    FILE_ATTRIBUTE_SYSTEM              = 0x00004  # noqa: E221
    FILE_ATTRIBUTE_RESERVED_0008       = 0x00008  # noqa: E221
    FILE_ATTRIBUTE_DIRECTORY           = 0x00010  # noqa: E221
    FILE_ATTRIBUTE_ARCHIVE             = 0x00020  # noqa: E221
    FILE_ATTRIBUTE_DEVICE              = 0x00040  # noqa: E221
    FILE_ATTRIBUTE_NORMAL              = 0x00080  # noqa: E221
    FILE_ATTRIBUTE_TEMPORARY           = 0x00100  # noqa: E221
    FILE_ATTRIBUTE_SPARSE_FILE         = 0x00200  # noqa: E221
    FILE_ATTRIBUTE_REPARSE_POINT       = 0x00400  # noqa: E221
    FILE_ATTRIBUTE_COMPRESSED          = 0x00800  # noqa: E221
    FILE_ATTRIBUTE_OFFLINE             = 0x01000  # noqa: E221
    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 0x02000  # noqa: E221  # pylint: disable=invalid-name
    FILE_ATTRIBUTE_ENCRYPTED           = 0x04000  # noqa: E221
    FILE_ATTRIBUTE_INTEGRITY_STREAM    = 0x08000  # noqa: E221
    FILE_ATTRIBUTE_VIRTUAL             = 0x10000  # noqa: E221
    FILE_ATTRIBUTE_NO_SCRUB_DATA       = 0x20000  # noqa: E221
    FILE_ATTRIBUTE_INVALID             = 0x0FFFF  # noqa: E221
# pylint: enable=bad-whitespace

    def __init__(self):
        self.logger = logging.getLogger('walker')

    def _init_misc(self, control_data):
        """ Initialize items """
        control_data['debug_queue'] = multiprocessing.Queue()
        control_data['ignored_file_pats'] = dtutils.compile_patterns(
            control_data['ignored_files'],
            control_data['ignore_path_case'],
        )
        control_data['ignored_dir_pats'] = dtutils.compile_patterns(
            control_data['ignored_dirs'],
            control_data['ignore_path_case'],
        )

    def _start_shared_memory(self, control_data):
        """ Initialize shared memory """
        control_data['buffer_blocks'] = []
        control_data['buffer_sizes'] = []
        control_data['buffer_names'] = []
        for _ in range(control_data['max_buffers']):
            if control_data['shm_mode']:
                buf = shared_memory.SharedMemory(create=True, size=control_data['max_block_size'])
                buffer_name = buf.name
                control_data['buffer_blocks'].append(buf)
                control_data['buffer_names'].append(buffer_name)
            else:
                control_data['buffer_blocks'].append([None])
            control_data['buffer_sizes'].append(0)

    def _end_shared_memory(self, control_data):
        """ Clean up shared memory """
        if control_data['shm_mode']:
            for i in range(control_data['max_buffers']):
                shm_buf = shared_memory.SharedMemory(name=control_data['buffer_names'][i])
                shm_buf.close()
                shm_buf.unlink()

    def _start_reader(self, control_data):
        """ Start long-running worker processes
            Until subprocessed are ended, raising exceptions can hang the parent process
        """
        control_data['reader_proc'] = None
        control_data['reader_cmd_queue'] = multiprocessing.Queue()
        control_data['reader_results_queue'] = multiprocessing.Queue()
        reader_proc = multiprocessing.Process(
            target=dtreader.reader_process,
            args=(
                control_data['debug_queue'],
                control_data['reader_cmd_queue'],
                control_data['reader_results_queue'],
                control_data['shm_mode'],
                control_data['max_block_size'],
            ),
        )
        reader_proc.name = '---Reader'
        reader_proc.start()

    def _end_reader(self, control_data):
        """ End reader subprocess """
        control_data['reader_cmd_queue'].put({
            'cmd': dtutils.Cmd.QUIT,
        })
        import time
        time.sleep(0.5)  # Because reasons
        while not control_data['reader_results_queue'].empty():
            retval = control_data['reader_results_queue'].get()
            self.logger.debug('Draining queue: %s', retval)
        dtutils.flush_debug_queue(control_data['debug_queue'], logging.getLogger('reader'))
        while control_data['reader_proc']:
            if control_data['reader_proc'] and not control_data['reader_proc'].is_alive():
                control_data['reader_proc'] = None

    def _start_workers(self, control_data):
        """ Start long-running worker processes
            Until subprocessed are ended, raising exceptions can hang the parent process
        """
        control_data['worker_procs'] = []
        control_data['worker_cmd_queues'] = []
        control_data['worker_results_queue'] = multiprocessing.Queue()
        for i in range(len(control_data['selected_digests'])):
            control_data['worker_cmd_queues'].append(multiprocessing.JoinableQueue())
            worker_proc = multiprocessing.Process(
                target=dtworker.worker_process,
                args=(
                    control_data['debug_queue'],
                    control_data['worker_cmd_queues'][i],
                    control_data['worker_results_queue'],
                    control_data['shm_mode'],
                ),
            )
            worker_proc.name = f'---Worker-{i}'
            worker_proc.start()
            control_data['worker_procs'].append(worker_proc)

    def _end_workers(self, control_data):
        """ End worker subprocesses """
        for worker_cmd_queue in control_data['worker_cmd_queues']:
            worker_cmd_queue.put({
                'cmd': dtutils.Cmd.QUIT,
            })
        while not control_data['worker_results_queue'].empty():
            retval = control_data['worker_results_queue'].get()
            self.logger.debug('Draining queue: %s', retval)
        dtutils.flush_debug_queue(control_data['debug_queue'], logging.getLogger('worker'))
        while any(control_data['worker_procs']):
            for i in range(len(control_data['selected_digests'])):
                if (control_data['worker_procs'][i] is not None) and (
                        not control_data['worker_procs'][i].is_alive()):
                    self.logger.debug(
                        'join %d (state = %s) at %f',
                        i,
                        control_data['worker_procs'][i].is_alive(),
                        dtutils.curr_time_secs(),
                    )
                    control_data['worker_procs'][i].join()
                    control_data['worker_procs'][i] = None

    def initialize(self, control_data):
        self._init_misc(control_data)
        self._start_shared_memory(control_data)
        self._start_reader(control_data)
        self._start_workers(control_data)

    def teardown(self, control_data):
        self._end_shared_memory(control_data)
        self._end_reader(control_data)
        self._end_workers(control_data)

    def get_win_filemode(self, elem):
        """ Windows: get system-specific file stats """
        return ctypes.windll.kernel32.GetFileAttributesW(elem)

    def is_win_symlink(self, elem):
        """ Windows: system-specific symlink check """
        return os.path.isdir(elem) and (
            self.get_win_filemode(elem) & self.FILE_ATTRIBUTE_REPARSE_POINT)

    def process_tree(self, control_data):
        """ Process the given directory tree """
        results = []
        self._walk_tree(
            control_data=control_data,
            root_dir=control_data['root_dir'],
            callback=self.visit_element,
            results=results)
        return results

    def _walk_tree(self, control_data, root_dir, callback, results):
        """ Re-entrant directory tree walker """
        try:
            dir_list = os.listdir(root_dir)
        except FileNotFoundError:
            self.logger.warning('FileNotFoundError %s', root_dir)
            control_data['counts']['errors'] += 1
            return
        except NotADirectoryError:
            self.logger.warning('NotADirectoryError %s', root_dir)
            control_data['counts']['errors'] += 1
            return
        except PermissionError:
            self.logger.warning('PermissionError %s', root_dir)
            control_data['counts']['errors'] += 1
            return
        print("Processing path {}".format(root_dir))
        for elem in sorted(dir_list):
            pathname = dtutils.unixify_path(os.path.join(root_dir, elem))
            # print("Processing file {}".format(pathname))
            try:
                stats = os.lstat(pathname)
            except FileNotFoundError:
                self.logger.warning('FileNotFoundError %s', root_dir)
                control_data['counts']['errors'] += 1
                continue
            if stat.S_ISDIR(stats.st_mode):
                if dtutils.elem_is_matched(
                        root_dir,
                        pathname,
                        control_data['ignored_dir_pats']):
                    self.logger.info('D IGNORED %s', pathname)
                    control_data['counts']['ignored'] += 1
                    continue
                results.append(self.visit_element(control_data, pathname, stats))
                self._walk_tree(
                    control_data=control_data,
                    root_dir=pathname,
                    callback=callback,
                    results=results)
            elif stat.S_ISREG(stats.st_mode):
                if dtutils.elem_is_matched(
                        root_dir,
                        pathname,
                        control_data['ignored_file_pats']):
                    self.logger.info('F IGNORED %s', pathname)
                    control_data['counts']['ignored'] += 1
                    continue
                results.append(self.visit_element(control_data, pathname, stats))
            else:
                results.append(self.visit_element(control_data, pathname, stats))
            dtutils.flush_debug_queue(control_data['debug_queue'], logging.getLogger('worker'))

    def visit_element(self, control_data, element, stats):
        """ Stat / digest a specific element found during the directory walk """
        root_dir = control_data['root_dir']
        elem_data = {}
        elem_data['name'] = dtutils.get_relative_path(root_dir, dtutils.unixify_path(element))
        elem_data['mode'] = stats.st_mode
        if sys.platform == 'win32':
            elem_data['mode_w'] = self.get_win_filemode(element)
        else:
            elem_data['mode_w'] = self.FILE_ATTRIBUTE_NONE
        elem_data['size'] = stats[stat.ST_SIZE]
        elem_data['atime'] = stats[stat.ST_ATIME]
        elem_data['mtime'] = stats[stat.ST_MTIME]
        elem_data['ctime'] = stats[stat.ST_CTIME]
        elem_data['digests'] = None
        elem_data['type'] = '?'
        alt_digest_len = 1
        if control_data['altfile_digest']:
            alt_digest_len = dtdigester.DIGEST_FUNCTIONS[control_data['altfile_digest']]['len']
        if sys.platform == 'win32' and self.is_win_symlink(element):
            elem_data['type'] = 'J'
            alt_digest = '?' * alt_digest_len
            sorted_digests = dtdigester.fill_digest_str(control_data, 'x')
        elif stat.S_ISDIR(stats.st_mode):
            elem_data['type'] = 'D'
            elem_data['size'] = 0
            alt_digest = '-' * alt_digest_len
            sorted_digests = dtdigester.fill_digest_str(control_data, '-')
            control_data['counts']['dirs'] += 1
        elif stat.S_ISREG(stats.st_mode):
            elem_data['type'] = 'F'
            elem_data['digests'] = dtdigester.digest_file(control_data, element)
            if elem_data['digests']:
                control_data['counts']['files'] += 1
                sorted_digests = '{' + ', '.join('{}: {}'.format(
                    i, elem_data['digests'][i]) for i in sorted(
                        elem_data['digests'])) + '}'
                if control_data['altfile_digest']:
                    alt_digest = elem_data['digests'][control_data['altfile_digest']]
            else:
                self.logger.warning('F Problems processing %s', element)
                control_data['counts']['errors'] += 1
                sorted_digests = dtdigester.fill_digest_str(control_data, '!')
                alt_digest = '!' * alt_digest_len
        else:
            elem_data['type'] = '?'
            sorted_digests = dtdigester.fill_digest_str(control_data, '?')
        file_details = '{};{};{:08x};{:08x};{:08x};{:04x};{:04x};{:010x};{}'.format(
            elem_data['type'],
            sorted_digests,
            elem_data['atime'], elem_data['mtime'], elem_data['ctime'],
            elem_data['mode'], elem_data['mode_w'],
            elem_data['size'],
            elem_data['name'])
        alt_digest = '-' * alt_digest_len
        if elem_data['type'] == 'D':
            alt_digest = '-' * alt_digest_len
        elif not elem_data['digests']:
            alt_digest = '?' * alt_digest_len
        elif control_data['altfile_digest']:
            alt_digest = elem_data['digests'][control_data['altfile_digest']]
        alt_details = '{};{:08x};{:08x};{:08x};{:04x};{:010x};{}'.format(
            alt_digest,
            elem_data['atime'], elem_data['mtime'], elem_data['ctime'],
            elem_data['mode_w'],
            elem_data['size'],
            elem_data['name'])
        self.logger.debug('%s', file_details)
        dtutils.outfile_write(control_data['outfile_name'], 'a', [
            '{}'.format(file_details),
        ])
        if control_data['altfile_digest']:
            dtutils.outfile_write(control_data['altfile_name'], 'a', [
                '{}'.format(alt_details),
            ])
        return elem_data
