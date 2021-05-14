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

import hashlib
import logging
import queue
import zlib

import dirtreedigest.utils as dtutils

if dtutils.shared_memory_available():
    from multiprocessing import shared_memory  # Python 3.8+
else:
    shared_memory = None


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


class CsumNoop0(CsumNoop):
    """ No-op digester """
    name = 'noop0'


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
DIGEST_FUNCTIONS_TEST = {
    # No-op test functions
    'noop':       {'name': 'noop',      'len':   8, 'entry': CsumNoop},  # noqa: E241
    'noop0':      {'name': 'noop0',     'len':   8, 'entry': CsumNoop0},  # noqa: E241
    'noop1':      {'name': 'noop1',     'len':   8, 'entry': CsumNoop1},  # noqa: E241
    'noop2':      {'name': 'noop2',     'len':   8, 'entry': CsumNoop2},  # noqa: E241
    'noop3':      {'name': 'noop3',     'len':   8, 'entry': CsumNoop3},  # noqa: E241
    'noop4':      {'name': 'noop4',     'len':   8, 'entry': CsumNoop4},  # noqa: E241
    'noop5':      {'name': 'noop5',     'len':   8, 'entry': CsumNoop5},  # noqa: E241
    'noop6':      {'name': 'noop6',     'len':   8, 'entry': CsumNoop6},  # noqa: E241
    'noop7':      {'name': 'noop7',     'len':   8, 'entry': CsumNoop7},  # noqa: E241
}
DIGEST_FUNCTIONS_MAIN = {
    # Digesters in Python since at least Python 2.7
    'crc32':      {'name': 'crc32',     'len':   8, 'entry': CsumCrc32},  # noqa: E241
    'adler32':    {'name': 'adler32',   'len':   8, 'entry': CsumAdler32},  # noqa: E241
    'md5':        {'name': 'md5',       'len':  32, 'entry': hashlib.md5},  # noqa: E241
    'sha1':       {'name': 'sha1',      'len':  40, 'entry': hashlib.sha1},  # noqa: E241
    'sha224':     {'name': 'sha224',    'len':  56, 'entry': hashlib.sha224},  # noqa: E241
    'sha256':     {'name': 'sha256',    'len':  64, 'entry': hashlib.sha256},  # noqa: E241
    'sha384':     {'name': 'sha384',    'len':  96, 'entry': hashlib.sha384},  # noqa: E241
    'sha512':     {'name': 'sha512',    'len': 128, 'entry': hashlib.sha512},  # noqa: E241
}
DIGEST_FUNCTIONS_PY36 = {
    # Digesters added in Python 3.6
    # Variable length digests are excluded (e.g., 'shake_128')
    'blake2b':    {'name': 'blake2b',   'len': 128, 'entry': hashlib.blake2b},  # noqa: E241
    'blake2s':    {'name': 'blake2s',   'len':  64, 'entry': hashlib.blake2s},  # noqa: E241
    'sha3_224':   {'name': 'sha3_224',  'len':  56, 'entry': hashlib.sha3_224},  # noqa: E241
    'sha3_256':   {'name': 'sha3_256',  'len':  64, 'entry': hashlib.sha3_256},  # noqa: E241
    'sha3_384':   {'name': 'sha3_384',  'len':  96, 'entry': hashlib.sha3_384},  # noqa: E241
    'sha3_512':   {'name': 'sha3_512',  'len': 128, 'entry': hashlib.sha3_512},  # noqa: E241
}
# pylint: enable=bad-whitespace, no-member
DIGEST_FUNCTIONS = {}
DIGEST_FUNCTIONS.update(DIGEST_FUNCTIONS_TEST)
DIGEST_FUNCTIONS.update(DIGEST_FUNCTIONS_MAIN)
DIGEST_FUNCTIONS.update(DIGEST_FUNCTIONS_PY36)


''' From least to most secure, excluding tests '''
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
    digest_list = sorted(digests_available)
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
        i, fillchar * DIGEST_FUNCTIONS[i]['len']) for i in sorted(
            control_data['selected_digests'])) + '}'


def digest_file(control_data, element):
    """ Digest a given element """
    logger = logging.getLogger('digester')
    start_time = dtutils.curr_time_secs()
    logger.debug('process_file(%s)', element)
    total_jobs = len(control_data['selected_digests'])
    bytes_read = 0
    found_eof = False
    hash_stats = {}

    control_data['reader_cmd_queue'].put({
        'cmd': dtutils.Cmd.INIT,
        'buf_names': control_data['buffer_names'],
        'element': element,
    })
    result = control_data['reader_results_queue'].get()
    dtutils.flush_debug_queue(control_data['debug_queue'], logging.getLogger('worker'))
    if result['errors']:
        return hash_stats

    for i, worker_cmd_queue in enumerate(control_data['worker_cmd_queues']):
        digest_name = control_data['selected_digests'][i]
        digest_func = DIGEST_FUNCTIONS[digest_name]['entry']
        worker_cmd_queue.put({
            'cmd': dtutils.Cmd.INIT,
            'digest_func': digest_func,
            'element': element,
        })

    while not found_eof:
        block_read = control_data['reader_results_queue'].get()
        logger.debug('BLOCK READ: %s %s %s', block_read['block_size'], block_read['buf_name'], element)
        found_eof = block_read['found_eof']
        block_size = block_read['block_size']
        buf_block = block_read['buf_block']
        buf_name = block_read['buf_name']
        bytes_read += block_size
        for worker_cmd_queue in control_data['worker_cmd_queues']:
            worker_cmd_queue.put({
                'cmd': dtutils.Cmd.PROCESS,
                'block_size': block_size,
                'buf_name': buf_name,  # Shared memory mode
                'buf_block': buf_block,  # Non-shared memory mode
                'element': element,
            })
        # Gather any intermediate outputs
        jobs = total_jobs
        while jobs > 0:
            try:
                result = control_data['worker_results_queue'].get_nowait()
            except queue.Empty:
                continue
            if result:
                jobs -= 1
        if buf_name:
            control_data['reader_cmd_queue'].put({
                'cmd': dtutils.Cmd.FREE,
                'buf_names': [buf_name],
            })

    for worker_cmd_queue in control_data['worker_cmd_queues']:
        worker_cmd_queue.put({
            'cmd': dtutils.Cmd.RESULT,
        })
    dtutils.flush_debug_queue(control_data['debug_queue'], logging.getLogger('worker'))
    jobs = total_jobs
    while jobs > 0:
        retval = control_data['worker_results_queue'].get()
        logger.debug('RETVAL: %s', retval)
        if 'msg' in retval:
            continue  #TODO: messages pop up here from time to time.
        hash_stats[retval['digest_name']] = retval['digest_value']
        jobs -= 1
    dtutils.flush_debug_queue(control_data['debug_queue'], logging.getLogger('worker'))

    end_time = dtutils.curr_time_secs()
    delta_time = end_time - start_time if end_time - start_time > 0 else 0.000001
    logger.debug('MAINLINE finished at %f', end_time)
    logger.debug(
        'run_time= %.3fs rate= %.3f MB/s bytes= %d %s',
        delta_time,
        bytes_read / 1024 / 1024 / delta_time,
        bytes_read,
        element)
    control_data['counts']['bytes_read'] += bytes_read
    return hash_stats
