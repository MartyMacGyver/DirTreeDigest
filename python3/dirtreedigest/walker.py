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

import os
import re
import stat
import ctypes
import logging
import mmap
import multiprocessing
import dirtreedigest.utils as dtutils
import dirtreedigest.worker as dtworker
import dirtreedigest.digester as dtdigester

# pylint: disable=bad-whitespace
class Walker(object):
    # Windows file attributes
    FILE_ATTRIBUTE_READONLY            = 0x00001
    FILE_ATTRIBUTE_HIDDEN              = 0x00002
    FILE_ATTRIBUTE_SYSTEM              = 0x00004
    FILE_ATTRIBUTE_RESERVED_0008       = 0x00008
    FILE_ATTRIBUTE_DIRECTORY           = 0x00010
    FILE_ATTRIBUTE_ARCHIVE             = 0x00020
    FILE_ATTRIBUTE_DEVICE              = 0x00040
    FILE_ATTRIBUTE_NORMAL              = 0x00080
    FILE_ATTRIBUTE_TEMPORARY           = 0x00100
    FILE_ATTRIBUTE_SPARSE_FILE         = 0x00200
    FILE_ATTRIBUTE_REPARSE_POINT       = 0x00400
    FILE_ATTRIBUTE_COMPRESSED          = 0x00800
    FILE_ATTRIBUTE_OFFLINE             = 0x01000
    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 0x02000  # pylint: disable=invalid-name
    FILE_ATTRIBUTE_ENCRYPTED           = 0x04000
    FILE_ATTRIBUTE_INTEGRITY_STREAM    = 0x08000
    FILE_ATTRIBUTE_VIRTUAL             = 0x10000
    FILE_ATTRIBUTE_NO_SCRUB_DATA       = 0x20000
    FILE_ATTRIBUTE_INVALID             = 0x0FFFF
# pylint: enable=bad-whitespace

    def __init__(self):
        self.logger = logging.getLogger('walker')

    def start_workers(self, control_data):
        control_data['p_worker_procs'] = []
        control_data['q_work_units'] = []
        control_data['q_results'] = multiprocessing.Queue()
        control_data['q_debug'] = multiprocessing.Queue()
        control_data['buffer_blocks'] = []
        control_data['buffer_sizes'] = []
        control_data['buffer_names'] = []
        for i in range(control_data['max_buffers']):
            buffer_name = '{}{}'.format(control_data['mmap_prefix'], i)
            control_data['buffer_names'].append(buffer_name)
            if control_data['mmap_mode']:
                control_data['buffer_blocks'].append(mmap.mmap(
                    -1,
                    control_data['max_block_size'],
                    buffer_name,
                ))
            else:
                control_data['buffer_blocks'].append([None])
            control_data['buffer_sizes'].append(0)
        for i in range(len(control_data['valid_digests'])):
            control_data['q_work_units'].append(multiprocessing.JoinableQueue())
            control_data['p_worker_procs'].append(multiprocessing.Process(
                target=dtworker.worker_process,
                args=(control_data['q_work_units'][i],
                      control_data['q_results'],
                      control_data['q_debug'],
                      control_data['mmap_mode'],
                     )
            ))
            #control_data['p_worker_procs'][i].daemon = True
            control_data['p_worker_procs'][i].start()
        # Until workers are ended, raising exceptions can hang the parent process

    def end_workers(self, control_data):
        # Signal processes that they're all done
        for q_work_unit in control_data['q_work_units']:
            q_work_unit.put((
                dtworker.WorkerSignal.QUIT,
                None,
                None,
            ))
        while not control_data['q_results'].empty():
            retval = control_data['q_results'].get(True)
            self.logger.debug('Draining queue: %s', retval)
        while any(control_data['p_worker_procs']):
            for i in range(len(control_data['valid_digests'])):
                if (control_data['p_worker_procs'][i] is not None) and (not control_data['p_worker_procs'][i].is_alive()):
                    self.logger.debug(
                        'join %d (state = %s) at %f',
                        i,
                        control_data['p_worker_procs'][i].is_alive(),
                        dtutils.curr_time_secs()
                    )
                    control_data['p_worker_procs'][i].join()
                    control_data['p_worker_procs'][i] = None
        dtutils.flush_debug_queue(control_data['q_debug'], logging.getLogger('worker'))

    def get_win_filemode(self, elem):
        return ctypes.windll.kernel32.GetFileAttributesW(elem)

    def is_win_symlink(self, elem):
        return os.path.isdir(elem) and (self.get_win_filemode(elem) & self.FILE_ATTRIBUTE_REPARSE_POINT)

    def split_win_drive(self, elem):
        m = re.match(r"^([a-zA-Z]:)(.*)$", elem)
        if m:
            return (m.group(1), m.group(2))
        return ('', elem)

    def remove_root(self, root, elem):
        matcher = r'^'+re.escape(dtutils.unixify_path(root))+r'(.*)$'
        retval = elem
        m = re.match(matcher, elem)
        if m:
            retval = m.group(1)
        if retval != '/':
            retval = retval.strip('/')
        return retval

    def compare_paths_nocase(self, path1, path2):
        path1_mod = dtutils.unixify_path(os.path.normpath(path1)).lower()
        path2_mod = dtutils.unixify_path(os.path.normpath(path2)).lower()
        return path1_mod == path2_mod

    def is_ignored_element(self, apath, ignored_elements):
        return self.split_win_drive(dtutils.unixify_path(os.path.normpath(apath)))[1] in ignored_elements

    def process_tree(self, control_data):
        '''Recurse directories with callback to process things'''
        results = []
        self._walk_tree(control_data=control_data, root_dir=control_data['root_dir'], callback=self.visit_element, results=results)
        return results

    def _walk_tree(self, control_data, root_dir, callback, results):
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
        for elem in sorted(dir_list):
            pathname = dtutils.unixify_path(os.path.join(root_dir, elem))
            stats = os.lstat(pathname)
            if stat.S_ISDIR(stats.st_mode):
                if self.is_ignored_element(pathname, control_data['ignored_dirs']):
                    self.logger.info('D IGNORED %s', pathname)
                    control_data['counts']['ignored'] += 1
                    continue
                results.append(self.visit_element(control_data, pathname, stats))
                self._walk_tree(control_data=control_data, root_dir=pathname, callback=callback, results=results)
            elif stat.S_ISREG(stats.st_mode):
                if self.is_ignored_element(pathname, control_data['ignored_files']):
                    self.logger.info('F IGNORED %s', pathname)
                    control_data['counts']['ignored'] += 1
                    continue
                results.append(self.visit_element(control_data, pathname, stats))
            else:
                results.append(self.visit_element(control_data, pathname, stats))
            dtutils.flush_debug_queue(control_data['q_debug'], logging.getLogger('worker'))

    def visit_element(self, control_data, element, stats):
        root_dir = control_data['root_dir']
        elem_data = {}
        elem_data['name'] = self.remove_root(root_dir, dtutils.unixify_path(element))
        elem_data['mode'] = stats.st_mode
        elem_data['mode_w'] = self.get_win_filemode(element)
        elem_data['size'] = stats[stat.ST_SIZE]
        elem_data['atime'] = stats[stat.ST_ATIME]
        elem_data['mtime'] = stats[stat.ST_MTIME]
        elem_data['ctime'] = stats[stat.ST_CTIME]
        elem_data['digests'] = None
        elem_data['type'] = '?'
        alt_digest_len = 1
        if control_data['altfile_digest']:
            alt_digest_len = dtdigester.digest_functions[control_data['altfile_digest']]['len']
        if self.is_win_symlink(element):
            elem_data['type'] = 'J'
            alt_digest = '?'*alt_digest_len
            sorted_digests = dtdigester.default_digests(control_data, 'x')
        elif stat.S_ISDIR(stats.st_mode):
            elem_data['type'] = 'D'
            elem_data['size'] = 0
            alt_digest = '-'*alt_digest_len
            sorted_digests = dtdigester.default_digests(control_data, '-')
            control_data['counts']['dirs'] += 1
        elif stat.S_ISREG(stats.st_mode):
            elem_data['type'] = 'F'
            elem_data['digests'] = dtdigester.digest_file(control_data, element)
            if elem_data['digests']:
                control_data['counts']['files'] += 1
                sorted_digests = '{' + ', '.join('{}: {}'.format(i, elem_data['digests'][i]) for i in sorted(elem_data['digests'])) + '}'
                #self.single_process_digest_test(control_data, element)
                if control_data['altfile_digest']:
                    alt_digest = elem_data['digests'][control_data['altfile_digest']]
            else:
                self.logger.warning('F Problems processing %s', element)
                control_data['counts']['errors'] += 1
                sorted_digests = dtdigester.default_digests(control_data, '!')
                alt_digest = '!'*alt_digest_len
        else:
            elem_data['type'] = '?'
            sorted_digests = dtdigester.default_digests(control_data, '?')
        file_details = '{};{};{:08x};{:08x};{:08x};{:04x};{:04x};{:010x};{}'.format(
            elem_data['type'],
            sorted_digests,
            elem_data['atime'], elem_data['mtime'], elem_data['ctime'],
            elem_data['mode'], elem_data['mode_w'],
            elem_data['size'],
            elem_data['name'])
        alt_digest = '-'*alt_digest_len
        if elem_data['type'] == 'D':
            alt_digest = '-'*alt_digest_len
        elif not elem_data['digests']:
            alt_digest = '?'*alt_digest_len
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
            '{}'.format(file_details),])
        if control_data['altfile_digest']:
            dtutils.outfile_write(control_data['altfile_name'], 'a', [
                '{}'.format(alt_details),])
        return elem_data

    def single_process_digest_test(self, control_data, element):
        digest_name = 'sha1'
        with dtutils.open_with_error_checking(element, 'rb') as (fileh, err):
            if err:
                return None
            mdf = dtdigester.digest_functions[digest_name]['func']()
            bytes_read = 0
            while True:
                byte_block = fileh.read(control_data['max_block_size'])
                bytes_read += len(byte_block)
                if not byte_block:
                    break
                mdf.update(byte_block)
                self.logger.debug(
                    'single_process_digest_test() processing -- digest=%s l=%d d=%s',
                    digest_name, bytes_read, mdf.hexdigest())
            self.logger.debug(
                'single_process_digest_test() FINAL -- digest=%s l=%d d=%s',
                digest_name, bytes_read, mdf.hexdigest())
