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

import sys
import os
import logging
import time
import dirtreedigest.config as dtconfig
import dirtreedigest.utils as dtutils
import dirtreedigest.walker as dtwalker
import dirtreedigest.digester as dtdigester

def main():
    control_data = dtconfig.control_data

    if not(len(sys.argv) > 1 and sys.argv[1] != ''):
        return

    control_data['mmap_prefix'] = 'SHM_{}'.format(os.getpid())

    dtutils.start_logging(
        control_data['logfile_name'],
        control_data['logfile_level'],
        control_data['console_level'])
    logger = logging.getLogger('_main_')
    logger.info('Log begins')

    control_data['root_dir'] = dtutils.unixify_path(sys.argv[1])
    control_data['outfile_suffix'] = control_data['root_dir'].replace(':', '$').replace('/', '_')
    control_data['outfile_name'] = '{}-{}.{}'.format(
        control_data['outfile_prefix'],
        control_data['outfile_suffix'],
        control_data['outfile_ext'])
    if control_data['altfile_digest']:
        control_data['altfile_name'] = '{}-{}.{}.{}'.format(
            control_data['outfile_prefix'],
            control_data['outfile_suffix'],
            control_data['altfile_digest'],
            control_data['outfile_ext'])
    control_data['valid_digests'] = dtdigester.get_digest_list(control_data=control_data)
    if not control_data['valid_digests']:
        return
    if control_data['altfile_digest']:
        if control_data['altfile_digest'] not in control_data['valid_digests']:
            logger.error('alt digest %s must be in valid digests',
                         control_data['altfile_digest'])
            return
    header1 = [
        '#{}'.format('-'*78),
        '#',
        '#  Base path: {}'.format(control_data['root_dir']),
        '#',
        '#{}'.format('-'*78),
    ]
    header2 = [
        '#{}'.format('-'*78),
        '',
    ]
    logger.info('Main output: %s', control_data['outfile_name'])
    dtutils.outfile_write(
        control_data['outfile_name'],
        'w',
        header1 + [control_data['outfile_header']] + header2,
    )
    if control_data['altfile_digest']:
        logger.info('Alt1 output: %s', control_data['altfile_name'])
        dtutils.outfile_write(
            control_data['altfile_name'],
            'w',
            header1 + [control_data['altfile_header'].format(control_data['altfile_digest'])] + header2,
        )
    start_time = dtutils.curr_time_secs()
    logger.debug('MAINLINE starts - max_block_size=%d', control_data['max_block_size'])
    logger.debug('-;%s', dtdigester.default_digests(control_data=control_data))
    results = []
    walk_item = dtwalker.Walker()
    try:
        walk_item.start_workers(control_data=control_data)
        start_walk_time = dtutils.curr_time_secs()
        results = walk_item.process_tree(control_data=control_data)
        end_walk_time = dtutils.curr_time_secs()
        walk_item.end_workers(control_data=control_data)
    except KeyboardInterrupt:
        walk_item.end_workers(control_data=control_data)
        logger.error('Ctrl+C pressed: exiting')
        logging.shutdown()
        time.sleep(0.5)
        return
    #print()
    #pprint(results)
    #print()
    end_time = dtutils.curr_time_secs()
    run_time = end_time-start_time
    walk_time = end_walk_time - start_walk_time
    logger.info(
        'run_time= %.3fs rate= %.2f MB/s bytes= %d',
        run_time,
        (control_data['counts']['bytes_read']/(1024*1024))/walk_time,
        control_data['counts']['bytes_read'])
    footer = [
        '',
        '#{}'.format('-'*78),
        '#',
        '#  Processed: {:,d} file(s), {:,d} folder(s) ({:,d} ignored, {:,d} errors) comprising {:,d} bytes'.format(
            control_data['counts']['files'],
            control_data['counts']['dirs'],
            control_data['counts']['ignored'],
            control_data['counts']['errors'],
            control_data['counts']['bytes_read'],
        ),
        '#',
        '#{}'.format('-'*78),
    ]
    dtutils.outfile_write(control_data['outfile_name'], 'a', footer)
    if control_data['altfile_digest']:
        dtutils.outfile_write(control_data['altfile_name'], 'a', footer)
    logger.debug('MAINLINE ends - max_block_size=%d', control_data['max_block_size'])
    logger.info('Log ends')
