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
import sys

from pathlib import Path

import dirtreedigest.__config__ as dtconfig
import dirtreedigest.comparator as dtcompare
import dirtreedigest.utils as dtutils


def validate_args(headline):
    """ Validate command-line arguments """
    control_data = dtconfig.CONTROL_DATA
    # package_data = dtconfig.PACKAGE_DATA

    epilog = ''

    parser = argparse.ArgumentParser(
        # description=package_data['description'],
        epilog=epilog)
    parser.add_argument('file_left', nargs='?',
                        default=None, type=str, action='store',
                        help='First digest file')
    parser.add_argument('file_right', nargs='?',
                        default=None, type=str, action='store',
                        help='Second digest file')
    parser.add_argument('--title', dest='output_title', metavar='TITLE',
                        default=None, type=str, action='store',
                        help='alternate output title')
    parser.add_argument('--notimestamps', dest='notimestamps',
                        action='store_true',
                        help='ignore timestamps')
    parser.add_argument('--noattributes', dest='noattributes',
                        action='store_true',
                        help='ignore attributes')
    parser.add_argument('--nocase', dest='nocase',
                        action='store_true',
                        help='case insensitive matching')
    parser.add_argument('--debug', dest='debug',
                        action='store_true',
                        help='more debugging to the logfile')
    args = parser.parse_args()

    if not (args.file_left and args.file_right):
        parser.print_help()
        return False

    control_data['file_l'] = args.file_left
    control_data['file_r'] = args.file_right

    control_data['logfile_level'] = logging.INFO
    if args.debug:
        control_data['logfile_level'] = logging.DEBUG

    control_data['outfile_suffix'] = 'cmp'

    if args.output_title:
        output_title = args.output_title
    else:
        output_title = '{}-{}.{}'.format(
            control_data['outfile_prefix'],
            control_data['outfile_suffix'],
            f"{Path(control_data['file_l']).stem} vs {Path(control_data['file_r']).stem}",
        )

    control_data['outfile_name'] = '{}.{}'.format(
        output_title,
        'txt',
    )

    control_data['logfile_name'] = '{}.{}'.format(
        output_title,
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

    logger.info('Digest file L: %s', args.file_left)
    logger.info('Digest file R: %s', args.file_right)

    control_data['notimestamps'] = False
    if args.notimestamps:
        control_data['notimestamps'] = True
    logger.info('notimestamps: %s', control_data['notimestamps'])

    control_data['noattributes'] = False
    if args.notimestamps:
        control_data['noattributes'] = True
    logger.info('noattributes: %s', control_data['noattributes'])

    control_data['ignore_path_case'] = False
    if args.nocase:
        control_data['ignore_path_case'] = True
    logger.info('ignore_path_case: %s', control_data['ignore_path_case'])

    return True


def main():
    """ Main entry point """
    control_data = dtconfig.CONTROL_DATA
    package_data = dtconfig.PACKAGE_DATA

    headline = f"{package_data['name']} Comparator {package_data['version']}"

    print()
    print(headline)
    print()

    if not validate_args(headline=headline):
        return False

    logger = logging.getLogger('_main_')

    header1 = [
        '#{}'.format('-' * 78),
        '#',
        '#  Path L: {}'.format('x'),
        '#  Path R: {}'.format('y'),
        '#',
        '#{}'.format('-' * 78),
    ]
    header2 = [
        '#{}'.format('-' * 78),
        '',
    ]
    logger.info('Main output: %s', control_data['outfile_name'])
    outfile_header = '#         Digests               |'
    outfile_header += 'accessT |modifyT |createT |attr|watr|'
    outfile_header += '   size   |relative name'
    dtutils.outfile_write(
        control_data['outfile_name'],
        'w',
        header1 + [outfile_header] + header2,
    )
    # start_time = dtutils.curr_time_secs()
    logger.debug('MAINLINE starts')

    comparator = dtcompare.Comparator(control_data=control_data)

    comparator.compare(
        file_l=control_data['file_l'],
        file_r=control_data['file_r'],
    )

    # end_time = dtutils.curr_time_secs()
    # delta_time = end_time - start_time
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
    logger.debug('MAINLINE ends')
    logger.info('Log ends')

    print()
    print(f"Main output: {control_data['outfile_name']}")
