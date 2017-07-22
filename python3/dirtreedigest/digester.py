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
import hashlib
import zlib
import logging
import dirtreedigest.utils as dtutils
import dirtreedigest.worker as dtworker

class CsumNoop(object):
    name = 'noop'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop1(object):
    name = 'noop1'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop2(object):
    name = 'noop2'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop3(object):
    name = 'noop3'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop4(object):
    name = 'noop4'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop5(object):
    name = 'noop5'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop6(object):
    name = 'noop6'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop7(object):
    name = 'noop7'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop8(object):
    name = 'noop8'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        pass
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumAdler32(object):
    name = 'adler32'
    def __init__(self):
        self.checksum = 1
    def update(self, msg):
        self.checksum = zlib.adler32(msg, self.checksum)
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumCrc32(object):
    name = 'crc32'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        self.checksum = zlib.crc32(msg, self.checksum)
    def hexdigest(self):
        return '{0:0{1}x}'.format(self.checksum, 8)

# pylint: disable=bad-whitespace, no-member
digest_functions = {
    'noop':       {'name': 'noop',      'len':   8, 'func': CsumNoop},
    'noop1':      {'name': 'noop1',     'len':   8, 'func': CsumNoop1},
    'noop2':      {'name': 'noop2',     'len':   8, 'func': CsumNoop2},
    'noop3':      {'name': 'noop3',     'len':   8, 'func': CsumNoop3},
    'noop4':      {'name': 'noop4',     'len':   8, 'func': CsumNoop4},
    'noop5':      {'name': 'noop5',     'len':   8, 'func': CsumNoop5},
    'noop6':      {'name': 'noop6',     'len':   8, 'func': CsumNoop6},
    'noop7':      {'name': 'noop7',     'len':   8, 'func': CsumNoop7},
    'noop8':      {'name': 'noop8',     'len':   8, 'func': CsumNoop8},
    'crc32':      {'name': 'crc32',     'len':   8, 'func': CsumCrc32},
    'adler32':    {'name': 'adler32',   'len':   8, 'func': CsumAdler32},
    'md5':        {'name': 'md5',       'len':  32, 'func': hashlib.md5},
    'sha1':       {'name': 'sha1',      'len':  40, 'func': hashlib.sha1},
    'sha224':     {'name': 'sha224',    'len':  56, 'func': hashlib.sha224},
    'sha256':     {'name': 'sha256',    'len':  64, 'func': hashlib.sha256},
    'sha384':     {'name': 'sha384',    'len':  96, 'func': hashlib.sha384},
    'sha512':     {'name': 'sha512',    'len': 128, 'func': hashlib.sha512},
    'blake2b':    {'name': 'blake2b',   'len': 128, 'func': hashlib.blake2b},
    'blake2s':    {'name': 'blake2s',   'len':  64, 'func': hashlib.blake2s},
    'sha3_224':   {'name': 'sha3_224',  'len':  56, 'func': hashlib.sha3_224},
    'sha3_256':   {'name': 'sha3_256',  'len':  64, 'func': hashlib.sha3_256},
    'sha3_384':   {'name': 'sha3_384',  'len':  96, 'func': hashlib.sha3_384},
    'sha3_512':   {'name': 'sha3_512',  'len': 128, 'func': hashlib.sha3_512},
    #'shake_128': {'name': 'shake_128', 'len':  32, 'func': hashlib.shake_128},
    #'shake_256': {'name': 'shake_256', 'len':  64, 'func': hashlib.shake_256},
}
# pylint: enable=bad-whitespace, no-member

def get_digest_list(control_data):
    ''' returns list of available digests '''
    logger = logging.getLogger('digester')
    digests_available = set(digest_functions.keys()) & set(control_data['given_digests'])
    digests_not_found = set(control_data['given_digests']) - digests_available
    if digests_not_found:
        logger.warning('Warning: invalid digest(s): %s', digests_not_found)
    digest_list = sorted(list(digests_available))
    if len(digest_list) > control_data['max_concurrent_jobs']:
        logger.error(
            'Error: Number of digests (%d) may not exceed max jobs (%d)',
            len(digest_list), control_data['max_concurrent_jobs'])
        return None
    logger.debug('Digests: %s', digest_list)
    return digest_list

def default_digests(control_data, fillchar='-'):
    return '{' + ', '.join('{}: {}'.format(i, fillchar*digest_functions[i]['len']) for i in sorted(control_data['valid_digests'])) + '}'

def digest_file(control_data, element):
    logger = logging.getLogger('digester')
    start_time = dtutils.curr_time_secs()
    logger.debug('process_file(%s)', element)
    curr_buffer_index = next_buffer_index = 0
    total_jobs = len(control_data['valid_digests'])
    buffers_in_use = 0
    active_jobs = 0
    bytes_read = 0
    found_eof = False
    buffer_full = False
    hash_stats = {}
    file_size = os.path.getsize(element)
    with dtutils.open_with_error_checking(element, 'rb') as (fileh, err):
        if err:
            return None
        for i, q_work_unit in enumerate(control_data['q_work_units']):
            digest_name = control_data['valid_digests'][i]
            digest_func = digest_functions[digest_name]['func']
            q_work_unit.put((
                dtworker.WorkerSignal.INIT,
                digest_func,
                None,
            ))
        # Process one block buffer completely before the next
        block_read = fileh.read(min(control_data['max_block_size'], file_size-bytes_read))
        if control_data['mmap_mode']:
            control_data['buffer_blocks'][curr_buffer_index].seek(0)
            control_data['buffer_blocks'][curr_buffer_index].write(block_read)
        else:
            control_data['buffer_blocks'][curr_buffer_index] = block_read
        block_len = len(block_read)
        control_data['buffer_sizes'][curr_buffer_index] = block_len
        bytes_read += block_len
        buffers_in_use = 1
        while buffers_in_use:
            active_jobs = 0
            completed_jobs = 0
            next_job = 0
            while completed_jobs < total_jobs: # per buffered block
                while next_job < total_jobs:
                    logger.debug(
                        'QUEUEING JOB %d with buffer #%d',
                        next_job, curr_buffer_index)
                    q_work_unit = control_data['q_work_units'][next_job]
                    if control_data['mmap_mode']:
                        q_work_unit.put((
                            dtworker.WorkerSignal.PROCESS,
                            control_data['buffer_names'][curr_buffer_index],
                            control_data['buffer_sizes'][curr_buffer_index],
                        ))
                    else:
                        # Note: This is noticably more costly versus shared memory mapping
                        q_work_unit.put((
                            dtworker.WorkerSignal.PROCESS,
                            control_data['buffer_blocks'][curr_buffer_index],
                            control_data['buffer_sizes'][curr_buffer_index],
                        ))
                    active_jobs += 1
                    next_job += 1
                    if active_jobs > total_jobs:
                        logger.warning(
                            'active_jobs %d > digests %d',
                            active_jobs, total_jobs)
                    if active_jobs == control_data['max_concurrent_jobs']:
                        logger.debug(
                            'active_jobs %d == max_concurrent %d',
                            active_jobs, control_data['max_concurrent_jobs'])
                        break
                logger.debug('ACTIVE JOBS A %d', active_jobs)
                while True:
                    # Prefetch while we wait for active jobs to start completing
                    # We always need at least one buffered item if not eof
                    if not found_eof:
                        new_buffer_index = (next_buffer_index + 1) % control_data['max_buffers']
                        if new_buffer_index != curr_buffer_index:
                            next_buffer_index = new_buffer_index
                            buffer_full = False
                            if control_data['mmap_mode']:
                                block_read = fileh.read(min(control_data['max_block_size'], file_size-bytes_read))
                            else:
                                block_read = fileh.read(min(control_data['max_block_size'], file_size-bytes_read))
                            if not block_read:
                                found_eof = True
                                logger.debug('eof found')
                                continue
                            block_len = len(block_read)
                            bytes_read += block_len
                            if control_data['mmap_mode']:
                                control_data['buffer_blocks'][next_buffer_index].seek(0)
                                control_data['buffer_blocks'][next_buffer_index].write(block_read)
                            else:
                                control_data['buffer_blocks'][next_buffer_index] = block_read
                            control_data['buffer_sizes'][next_buffer_index] = block_len
                            buffers_in_use += 1
                            logger.debug(
                                'prefetched %d bytes into buffer #%d bufs_in_use %d (%s)',
                                len(block_read), next_buffer_index,
                                buffers_in_use, element)
                        else:
                            # Otherwise the ring buffer is full so we do nothing more
                            if not buffer_full:
                                logger.debug(
                                    'prefetch buffer is currently full - bufs_in_use %d',
                                    buffers_in_use)
                                buffer_full = True
                    if not control_data['q_results'].empty():
                        break
                dtutils.flush_debug_queue(control_data['q_debug'], logging.getLogger('worker'))
                while not control_data['q_results'].empty():
                    retval = control_data['q_results'].get(True)
                    logger.debug('Returned: %s', retval)
                    completed_jobs += 1
                    active_jobs -= 1
                logger.debug('ACTIVE JOBS B %d', active_jobs)
            logger.debug(
                'Finished buffer #%d cnt was %d of %d bytes',
                curr_buffer_index,
                buffers_in_use,
                control_data['buffer_sizes'][curr_buffer_index])
            curr_buffer_index = (curr_buffer_index + 1) % control_data['max_buffers']
            buffers_in_use -= 1
        for q_work_unit in control_data['q_work_units']:
            q_work_unit.put((
                dtworker.WorkerSignal.RESULT,
                None,
                None,
            ))
        dtutils.flush_debug_queue(control_data['q_debug'], logging.getLogger('worker'))
        rolloff = total_jobs
        while rolloff > 0:
            retval = control_data['q_results'].get(True)
            logger.debug('RETVAL: %s', retval)
            if not isinstance(retval, tuple):
                logger.warning('retval is not finalized')
                continue
            hash_stats[retval[0]] = retval[1]
            rolloff -= 1
        dtutils.flush_debug_queue(control_data['q_debug'], logging.getLogger('worker'))
    end_time = dtutils.curr_time_secs()
    run_time = end_time-start_time
    logger.debug('MAINLINE finished at %f', end_time)
    logger.debug(
        'run_time= %.3fs rate= %.2f MB/s bytes= %d %s',
        run_time,
        (bytes_read/(1024*1024))/run_time,
        bytes_read,
        element)
    control_data['counts']['bytes_read'] += bytes_read
    return hash_stats
