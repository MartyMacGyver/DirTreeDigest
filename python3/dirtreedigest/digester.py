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
import sys
import hashlib
import zlib
import logging
import dirtreedigest.utils as dtutils
import dirtreedigest.worker as dtworker

class CsumNoop(object):
    """ No-op digester """
    name = 'noop'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        """ Update checksum """
        pass
    def hexdigest(self):
        """ Return digest string in hexadecimal format """
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumNoop1(CsumNoop):
    """ No-op digester """
    name = 'noop1'

class CsumNoop2(CsumNoop):
    """ No-op digester """
    name = 'noop2'

class CsumNoop3(CsumNoop):
    """ No-op digester """
    name = 'noop3'

class CsumNoop4(CsumNoop):
    """ No-op digester """
    name = 'noop4'

class CsumNoop5(CsumNoop):
    """ No-op digester """
    name = 'noop5'

class CsumNoop6(CsumNoop):
    """ No-op digester """
    name = 'noop6'

class CsumNoop7(CsumNoop):
    """ No-op digester """
    name = 'noop7'

class CsumNoop8(CsumNoop):
    """ No-op digester """
    name = 'noop8'

class CsumAdler32(object):
    """ Adler32 digester """
    name = 'adler32'
    def __init__(self):
        self.checksum = 1
    def update(self, msg):
        """ Update checksum """
        self.checksum = zlib.adler32(msg, self.checksum)
    def hexdigest(self):
        """ Return digest string in hexadecimal format """
        return '{0:0{1}x}'.format(self.checksum, 8)

class CsumCrc32(object):
    """ CRC32 digester """
    name = 'crc32'
    def __init__(self):
        self.checksum = 0
    def update(self, msg):
        """ Update checksum """
        self.checksum = zlib.crc32(msg, self.checksum)
    def hexdigest(self):
        """ Return digest string in hexadecimal format """
        return '{0:0{1}x}'.format(self.checksum, 8)

# pylint: disable=bad-whitespace, no-member
DIGEST_FUNCTIONS = {
    'noop':       {'name': 'noop',      'len':   8, 'entry': CsumNoop},
    'noop1':      {'name': 'noop1',     'len':   8, 'entry': CsumNoop1},
    'noop2':      {'name': 'noop2',     'len':   8, 'entry': CsumNoop2},
    'noop3':      {'name': 'noop3',     'len':   8, 'entry': CsumNoop3},
    'noop4':      {'name': 'noop4',     'len':   8, 'entry': CsumNoop4},
    'noop5':      {'name': 'noop5',     'len':   8, 'entry': CsumNoop5},
    'noop6':      {'name': 'noop6',     'len':   8, 'entry': CsumNoop6},
    'noop7':      {'name': 'noop7',     'len':   8, 'entry': CsumNoop7},
    'noop8':      {'name': 'noop8',     'len':   8, 'entry': CsumNoop8},
    'crc32':      {'name': 'crc32',     'len':   8, 'entry': CsumCrc32},
    'adler32':    {'name': 'adler32',   'len':   8, 'entry': CsumAdler32},
    'md5':        {'name': 'md5',       'len':  32, 'entry': hashlib.md5},
    'sha1':       {'name': 'sha1',      'len':  40, 'entry': hashlib.sha1},
    'sha224':     {'name': 'sha224',    'len':  56, 'entry': hashlib.sha224},
    'sha256':     {'name': 'sha256',    'len':  64, 'entry': hashlib.sha256},
    'sha384':     {'name': 'sha384',    'len':  96, 'entry': hashlib.sha384},
    'sha512':     {'name': 'sha512',    'len': 128, 'entry': hashlib.sha512},
}
if sys.version_info >= (3,6):
    DIGEST_FUNCTIONS36 = {
        'blake2b':    {'name': 'blake2b',   'len': 128, 'entry': hashlib.blake2b},
        'blake2s':    {'name': 'blake2s',   'len':  64, 'entry': hashlib.blake2s},
        'sha3_224':   {'name': 'sha3_224',  'len':  56, 'entry': hashlib.sha3_224},
        'sha3_256':   {'name': 'sha3_256',  'len':  64, 'entry': hashlib.sha3_256},
        'sha3_384':   {'name': 'sha3_384',  'len':  96, 'entry': hashlib.sha3_384},
        'sha3_512':   {'name': 'sha3_512',  'len': 128, 'entry': hashlib.sha3_512},
        #'shake_128': {'name': 'shake_128', 'len':  32, 'entry': hashlib.shake_128},
        #'shake_256': {'name': 'shake_256', 'len':  64, 'entry': hashlib.shake_256},
    }
    DIGEST_FUNCTIONS.update(DIGEST_FUNCTIONS36)
# pylint: enable=bad-whitespace, no-member

''' From least to most secure, excluding noops '''
DIGEST_PRIORITY = [
    'crc32',
    'adler32',
    'md5',
    'sha1',
    'sha224',
    'sha3_224',
    'sha256',
    'blake2s',
    'sha3_256',
    'sha384',
    'sha3_384',
    'sha512',
    'blake2b',
    'sha3_512',
]

def validate_digests(control_data):
    """ returns list of available digests """
    logger = logging.getLogger('digester')
    if not control_data['selected_digests']:
        return None
    digests_available = set(DIGEST_FUNCTIONS.keys()) & set(control_data['selected_digests'])
    digests_not_found = set(control_data['selected_digests']) - digests_available
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

def fill_digest_str(control_data, fillchar='-'):
    """ Create a padded dummy digest value """
    return '{' + ', '.join('{}: {}'.format(
        i, fillchar*DIGEST_FUNCTIONS[i]['len']) for i in sorted(
            control_data['selected_digests'])) + '}'

def digest_file(control_data, element):
    """ Digest a given element """
    logger = logging.getLogger('digester')
    start_time = dtutils.curr_time_secs()
    logger.debug('process_file(%s)', element)
    curr_buffer_index = next_buffer_index = 0
    total_jobs = len(control_data['selected_digests'])
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
            digest_name = control_data['selected_digests'][i]
            digest_func = DIGEST_FUNCTIONS[digest_name]['entry']
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
                        if new_buffer_index == curr_buffer_index:
                            if not buffer_full:
                                logger.debug(
                                    'prefetch buffer is currently full - bufs_in_use %d',
                                    buffers_in_use)
                                buffer_full = True
                        else:
                            next_buffer_index = new_buffer_index
                            buffer_full = False
                            block_read = fileh.read(
                                min(control_data['max_block_size'], file_size-bytes_read))
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
