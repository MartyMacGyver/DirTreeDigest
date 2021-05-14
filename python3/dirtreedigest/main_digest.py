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

import argparse
import logging
import os
import sys

import dirtreedigest.__config__ as dtconfig
import dirtreedigest.digester as dtdigester
import dirtreedigest.utils as dtutils
import dirtreedigest.walker as dtwalker


def validate_args(headline):
    """ Validate command-line arguments """
    control_data = dtconfig.CONTROL_DATA
    # package_data = dtconfig.PACKAGE_DATA

    digest_list = sorted(dtdigester.DIGEST_FUNCTIONS.keys())
    epilog = "Digests available: {}".format(digest_list)

    parser = argparse.ArgumentParser(
        # description=package_data['description'],
        epilog=epilog)
    parser.add_argument('root', nargs='?', metavar='ROOTPATH',
                        default=None, type=str, action='store',
                        help='root directory for processing')
    parser.add_argument('--digests', dest='selected_digests',
                        metavar='DIGEST1[,DIGEST2...]',
                        default=','.join(control_data['default_digests']),
                        type=str, action='store',
                        help='digests to use')
    parser.add_argument('--altdigest', dest='altfile_digest', metavar='DIGEST',
                        default=None, type=str, action='store',
                        help='alternate single digest report')
    parser.add_argument('--title', dest='output_title', metavar='TITLE',
                        default=None, type=str, action='store',
                        help='alternate output title')
    parser.add_argument('--tstamp', dest='output_tstamp', metavar='TIMESTAMP',
                        default=None, type=str, action='store',
                        help='alternate output timestamp')
    parser.add_argument('--blocksize', dest='blocksize', metavar='MBYTES',
                        default=control_data['max_block_size_mb'], type=int, action='store',
                        help='block size in MB')
    parser.add_argument('--buffers', dest='buffers', metavar='N',
                        default=control_data['max_buffers'], type=int, action='store',
                        help='number of buffers')
    parser.add_argument('--noshm', dest='noshm',
                        action='store_true',
                        help='don\'t use shared memory')
    parser.add_argument('--nocase', dest='nocase',
                        action='store_true',
                        help='case insensitive matching')
    parser.add_argument('--debug', dest='debug',
                        action='store_true',
                        help='more debugging to the logfile')
    parser.add_argument('--xfiles', dest='excluded_files', metavar='FILE1[,FILE2...]',
                        default=None, type=str, action='append',
                        help='excluded files')
    parser.add_argument('--xdirs', dest='excluded_dirs', metavar='DIR1[,DIR2...]',
                        default=None, type=str, action='append',
                        help='excluded directories')
    args = parser.parse_args()

    if not args.root:
        parser.print_help()
        return False

    control_data['logfile_level'] = logging.INFO
    if args.debug:
        control_data['logfile_level'] = logging.DEBUG

    control_data['root_dir'] = dtutils.unixify_path(os.path.realpath(args.root))

    control_data['outfile_suffix'] = control_data['root_dir'].replace(':', '$').replace('/', '_')

    if args.output_title:
        output_title = args.output_title
    else:
        output_title = '{}-{}'.format(
            control_data['outfile_prefix'],
            control_data['outfile_suffix'],
        )

    if args.output_tstamp:
        output_tstamp = args.output_tstamp
    else:
        output_tstamp = dtutils.datetime_as_str()

    control_data['outfile_name'] = '{}.{}.{}'.format(
        output_title,
        output_tstamp,
        control_data['outfile_ext'],
    )

    control_data['logfile_name'] = '{}.{}.{}'.format(
        output_title,
        output_tstamp,
        control_data['logfile_ext'],
    )

    dtutils.start_logging(
        control_data['logfile_name'],
        control_data['logfile_level'],
        control_data['console_level'],
    )

    logger = logging.getLogger('_main_')
    logger.info('Log begins')
    logger.info('-' * 78)
    logger.info(headline)
    logger.info(f"Using Python {sys.version}")
    logger.info('-' * 78)

    logger.info('Root dir (gvn): %s', args.root)
    logger.info('Root dir (mod): %s', control_data['root_dir'])
    if not os.path.isdir(os.path.realpath(args.root)):
        logger.error('Root dir is not a directory / does not exist!')
        return False

    if not 1 <= args.blocksize < 1024:
        logger.error('Block size must be >= 1MB and < 1024 MB')
        return False
    control_data['max_block_size_mb'] = args.blocksize
    control_data['max_block_size'] = args.blocksize * 1024 * 1024
    logger.info('max_block_size: %d MB', control_data['max_block_size_mb'])

    if not 2 <= args.buffers <= 32:
        logger.error('Number of buffers must be >= 2 and <= 32')
        return False
    control_data['max_buffers'] = args.buffers
    logger.info('max_buffers: %d', control_data['max_buffers'])

    control_data['shm_mode'] = True
    if args.noshm or not dtutils.shared_memory_available():
        control_data['shm_mode'] = False
    logger.info('shm_mode: %s', control_data['shm_mode'])

    control_data['ignore_path_case'] = False
    if args.nocase:
        control_data['ignore_path_case'] = True
    logger.info('ignore_path_case: %s', control_data['ignore_path_case'])

    if args.selected_digests:
        arg_mod = ' '.join(args.selected_digests.replace(',', ' ').split())
        control_data['selected_digests'] = arg_mod.split(' ')
    control_data['selected_digests'] = dtdigester.validate_digests(control_data=control_data)
    if not control_data['selected_digests']:
        logger.error('No valid digests selected')
        return False
    logger.info('digests to run: %s', ', '.join(control_data['selected_digests']))

    if args.excluded_files:
        for val in args.excluded_files:
            control_data['ignored_files'].append(val)
    logger.info('ignored_files: %s', ', '.join(control_data['ignored_files']))

    if args.excluded_dirs:
        for val in args.excluded_dirs:
            control_data['ignored_dirs'].append(val)
    logger.info('ignored_dirs: %s', ', '.join(control_data['ignored_dirs']))

    if args.altfile_digest:
        control_data['altfile_digest'] = args.altfile_digest.lower()
        if control_data['altfile_digest'] not in control_data['selected_digests']:
            logger.error('alt digest %s must be in selected digests',
                         control_data['altfile_digest'])
            return False
        control_data['altfile_name'] = '{}.{}.{}.{}'.format(
            output_title,
            control_data['altfile_digest'],
            output_tstamp,
            control_data['outfile_ext'],
        )
    return True


def main():
    """ Main entry point """
    control_data = dtconfig.CONTROL_DATA
    package_data = dtconfig.PACKAGE_DATA

    headline = f"{package_data['name']} Digester {package_data['version']}"

    print()
    print(headline)
    print()

    if not validate_args(headline):
        return False

    logger = logging.getLogger('_main_')

    header1 = [
        '#{}'.format('-' * 78),
        '#',
        '#  Base path: {}'.format(control_data['root_dir']),
        '#',
        '#{}'.format('-' * 78),
    ]
    header2 = [
        '#{}'.format('-' * 78),
        '',
    ]

    logger.debug('Logging out: %s', control_data['logfile_name'])
    logger.debug('Main output: %s', control_data['outfile_name'])

    outfile_header = '#         Digests               |'
    outfile_header += 'accessT |modifyT |createT |attr|watr|'
    outfile_header += '   size   |relative name'
    dtutils.outfile_write(
        control_data['outfile_name'],
        'w',
        header1 + [outfile_header] + header2,
    )
    altfile_header = '#        {} signature          |'
    altfile_header += 'accessT |modifyT |createT |watr|'
    altfile_header += '   size   |relative name'
    if control_data['altfile_digest']:
        logger.info('Alt  output: %s', control_data['altfile_name'])
        dtutils.outfile_write(
            control_data['altfile_name'],
            'w',
            header1 + [altfile_header.format(control_data['altfile_digest'])] + header2,
        )

    start_time = dtutils.curr_time_secs()
    logger.debug('MAINLINE starts - max_block_size=%d', control_data['max_block_size'])
    logger.debug('-;%s', dtdigester.fill_digest_str(control_data=control_data))
    walk_item = dtwalker.Walker()
    try:
        walk_item.initialize(control_data=control_data)
        start_walk_time = dtutils.curr_time_secs()
        walk_item.process_tree(control_data=control_data)
        end_walk_time = dtutils.curr_time_secs()
        walk_item.teardown(control_data=control_data)
    except KeyboardInterrupt:
        walk_item.teardown(control_data=control_data)
        logger.error('Ctrl+C pressed: exiting')
        logging.shutdown()
        return False
    end_time = dtutils.curr_time_secs()
    delta_time = end_time - start_time if end_time - start_time > 0 else 0.000001
    delta_walk_time = end_walk_time - start_walk_time if end_walk_time - start_walk_time > 0 else 0.000001
    logger.info(
        'run_time= %.3fs walk_time= %.3fs rate= %.2f MB/s bytes= %d',
        delta_time,
        delta_walk_time,
        control_data['counts']['bytes_read'] / 1024 / 1024 / delta_walk_time,
        control_data['counts']['bytes_read'],
    )
    footer = [
        '',
        '#{}'.format('-' * 78),
        '#',
        '#  Processed: {:,d} file(s), {:,d} folder(s) ({:,d} ignored, {:,d} errors) comprising {:,d} bytes'.format(
            control_data['counts']['files'],
            control_data['counts']['dirs'],
            control_data['counts']['ignored'],
            control_data['counts']['errors'],
            control_data['counts']['bytes_read'],
        ),
        '#',
        '#{}'.format('-' * 78),
    ]
    dtutils.outfile_write(control_data['outfile_name'], 'a', footer)
    if control_data['altfile_digest']:
        dtutils.outfile_write(control_data['altfile_name'], 'a', footer)
    logger.debug('MAINLINE ends - max_block_size=%d', control_data['max_block_size'])
    logger.info('Log ends')

    print()
    print(f"Logging out: {control_data['logfile_name']}")
    print(f"Main output: {control_data['outfile_name']}")
