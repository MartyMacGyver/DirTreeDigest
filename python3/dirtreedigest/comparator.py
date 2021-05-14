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

import re
import logging
from collections import defaultdict
import dirtreedigest.digester as dtdigester
from enum import Enum


class DiffType(Enum):
    M_UNDEF = 0  # Undefined (error case)  # noqa: E221
    M_NONE  = 1  # Diff file Name, Diff Data ("no match" anywhere)  # noqa: E221
    M_SFSD  = 2  # Same Full name, Same Data (Opposite only)  # noqa: E221
    M_SFDD  = 3  # Same Full name, Diff Data (Opposite only)  # noqa: E221
    M_SNSD  = 4  # Same file Name, Same Data (Opposite and Same sides)  # noqa: E221
    M_DNSD  = 5  # Diff file Name, Same Data (Opposite and Same sides)  # noqa: E221


class Comparator(object):
    """ Digest blob comparator and supporting functions """
    elements_l = []
    elements_r = []
    files_by_name_l = {}
    files_by_name_r = {}
    rootpath_l = ''
    rootpath_r = ''
    best_digest = None
    control_data = None

    def __init__(self, control_data):
        self.logger = logging.getLogger('comparator')
        self.control_data = control_data

    def read_dtd_report(self, filename):
        element_pat = re.compile(
            r"^(.+?);{(.+?)};(.+?);(.+?);(.+?);(.+?);(.+?);(.+?);(.*)$")
        legacy_pat = re.compile(
            r"^(.+?);(.+?);(.+?);(.+?);(.+?);(.+?);(.*)$")
        rootpath_pat = re.compile(
            r"^#\s+Base path:\s+(.*)$")
        elements = []
        rootpath = ''
        with open(filename, 'r', encoding='utf-8') as fileh:
            for line in fileh:
                line = line.rstrip('\n')
                mval = element_pat.match(line)
                if mval:
                    digests = {}
                    for digestpair in mval[2].split(','):
                        (digest, val) = digestpair.strip().split(':')
                        digest = digest.strip()
                        val = val.strip()
                        digests[digest] = val
                    file_type = mval[1]
                    file_name = mval[9]
                    if file_type not in ['D', 'F']:
                        self.logger.warning(
                            "Ignoring file type '%s' for %s",
                            file_type,
                            file_name,
                        )
                    elem = {
                        'type': file_type,
                        'digests': digests,
                        'time_access': mval[3],
                        'time_modified': mval[4],
                        'time_created': mval[5],
                        'attr_std': mval[6],
                        'attr_win': mval[7],
                        'size': mval[8],
                        'fullname': file_name,
                    }
                    elements.append(elem)
                else:
                    mval = rootpath_pat.match(line)
                    if mval:
                        rootpath = mval[1]
                    else:
                        mval = legacy_pat.match(line)
                        if mval:
                            file_name = mval[7]
                            digests = {}
                            digests['md5'] = mval[1]
                            file_type = 'F'
                            if digests['md5'].startswith('?'):
                                file_type = '?'
                            elif digests['md5'].startswith('-'):
                                file_type = 'D'
                            if file_type not in ['D', 'F']:
                                self.logger.warning(
                                    "Ignoring file type '%s' for %s",
                                    file_type,
                                    file_name,
                                )
                            elem = {
                                'type': file_type,
                                'digests': digests,
                                'time_access': mval[2],
                                'time_modified': mval[3],
                                'time_created': mval[4],
                                'attr_std': '0000',
                                'attr_win': mval[5],
                                'size': mval[6],
                                'fullname': mval[7],
                            }
                            elements.append(elem)
        self.filesplit(elements)
        return (rootpath, elements)

    def choose_best_digest_for_compare(self, elems1, elems2):
        best = -1
        if not len(elems1) > 0 and len(elems2) > 0:
            self.logger.error('Cannot choose a digest - not found')
            return None
        if 'digests' not in elems1[0] and 'digests' in elems2[0]:
            self.logger.error('Cannot choose a digest - not found')
            return None
        s1 = set(elems1[0]['digests'])
        s2 = set(elems2[0]['digests'])
        for digest in (s1 & s2):
            if digest in dtdigester.DIGEST_PRIORITY:
                best = max(best, dtdigester.DIGEST_PRIORITY.index(digest))
        if best < 0:
            self.logger.error('Cannot choose a digest - none in common')
            return None
        best_name = dtdigester.DIGEST_PRIORITY[best]
        return best_name

    def filesplit(self, elements):
        for elem in elements:
            if '/' in elem['fullname']:
                (elem['pathpart'], elem['filepart']) = elem['fullname'].rsplit('/', 1)
            else:
                (elem['pathpart'], elem['filepart']) = ('', elem['fullname'])
            # print(path, name)

    def compare(self, file_l, file_r):
        """ Main entry: compare two dirtreedigest reports """
        (self.rootpath_l, self.elements_l) = self.read_dtd_report(file_l)
        (self.rootpath_r, self.elements_r) = self.read_dtd_report(file_r)
        self.best_digest = self.choose_best_digest_for_compare(
            self.elements_l, self.elements_r)
        if self.best_digest is None:
            return None
        (self.files_by_name_l, self.files_by_digest_l) = self.slice_data(
            self.elements_l)
        (self.files_by_name_r, self.files_by_digest_r) = self.slice_data(
            self.elements_r)

        name_set_l = set(self.files_by_name_l)
        name_set_r = set(self.files_by_name_r)
        name_diff_l = name_set_l - name_set_r
        name_diff_r = name_set_r - name_set_l
        name_same = name_set_r & name_set_l

        (elems_changed) = self.compare_by_full_names(name_same)
        (elems_copied, elems_added) = self.check_rhs(name_diff_r)
        (elems_moved, elems_deleted) = self.check_lhs(name_diff_l)

        for elem in sorted(elems_changed, key=lambda k: k['fullname']):
            self.logger.info("CHANGED {}".format(elem['fullname']))
        for elem in sorted(elems_copied, key=lambda k: k['fullname']):
            self.logger.info("COPIED  {} == {}".format(elem['fullname'], '---'))
        for elem in sorted(elems_added, key=lambda k: k['fullname']):
            self.logger.info("ADDED   {}".format(elem['fullname']))
        for elem in sorted(elems_moved, key=lambda k: k['fullname']):
            self.logger.info("MOVED   {} == {}".format(elem['fullname'], '---'))
        for elem in sorted(elems_deleted, key=lambda k: k['fullname']):
            self.logger.info("DELETED {}".format(elem['fullname']))

        self.logger.info("Root L: %s", self.rootpath_l)
        self.logger.info("Root R: %s", self.rootpath_r)
        self.logger.info("BestDG: %s", self.best_digest)
        self.logger.info("ElemsL: %d", len(self.elements_l))
        self.logger.info("ElemsR: %d", len(self.elements_r))
        self.logger.info("FilesL: %d", len(self.files_by_name_l))
        self.logger.info("FilesR: %d", len(self.files_by_name_r))
        self.logger.info("  Both: %d", len(name_same))
        self.logger.info("Only L: %d", len(name_diff_l))
        self.logger.info("Only R: %d", len(name_diff_r))

    def slice_data(self, elements):
        files_by_name = {
            elem['fullname']: elem for elem in elements if elem['type'] == 'F'}
        files_by_digest = defaultdict(list)
        for elem in elements:
            if elem['type'] == 'F':
                cmp_digest = elem['digests'][self.best_digest]
                files_by_digest[cmp_digest].append(elem)
        return (files_by_name, files_by_digest)

    def compare_by_full_names(self, name_same):
        elems_changed = []
        for name in name_same:
            digest_l = self.files_by_name_l[name]['digests'][self.best_digest]
            digest_r = self.files_by_name_r[name]['digests'][self.best_digest]
            self.files_by_name_l[name]['match'] = [self.files_by_digest_r[digest_l]]
            self.files_by_name_r[name]['match'] = [self.files_by_digest_l[digest_r]]
            if digest_l == digest_r:
                self.files_by_name_l[name]['status'] = 'same'
                self.files_by_name_r[name]['status'] = 'same'
            else:
                self.files_by_name_l[name]['status'] = 'changed'
                self.files_by_name_r[name]['status'] = 'changed'
                # self.logger.info("Digest changed: %s", name)
                elems_changed.append(self.files_by_name_r[name])
        return (elems_changed)

    def check_rhs(self, name_diff_r):
        elems_copied = []
        elems_added = []
        for name in name_diff_r:
            digest_r = self.files_by_name_r[name]['digests'][self.best_digest]
            # print("checking", name)
            if digest_r in self.files_by_digest_l:
                # print(name, digest_r)
                # matched_elems = [elem['fullname'] for elem in self.files_by_digest_l[digest_r]]
                # matched_names = ','.join(matched_elems)
                # print("> COPIED  {} == {}".format(name, matched_names))
                self.files_by_name_r[name]['status'] = 'copied'
                for elem in self.files_by_digest_l[digest_r]:
                    if elem['filepart'] == self.files_by_name_r[name]['filepart']:
                        print("Found likely source", self.files_by_name_r[name]['fullname'])
                        break
                self.files_by_name_r[name]['match'] = self.files_by_digest_l[digest_r]
                elems_copied.append(self.files_by_name_r[name])
            else:
                # print("> ADDED   {}".format(name))
                self.files_by_name_r[name]['status'] = 'added'
                elems_added.append(self.files_by_name_r[name])
        return (elems_copied, elems_added)

    def check_lhs(self, name_diff_l):
        elems_moved = []
        elems_deleted = []
        for name in name_diff_l:
            digest_l = self.files_by_name_l[name]['digests'][self.best_digest]
            # print("checking", name)
            if digest_l in self.files_by_digest_r:
                # print(name, digest_l)
                # matched_elems = [elem['fullname'] for elem in self.files_by_digest_r[digest_l]]
                # matched_names = ','.join(matched_elems)
                # print("< MOVED   {} == {}".format(name, matched_names))
                self.files_by_name_l[name]['status'] = 'moved'
                self.files_by_name_l[name]['match'] = self.files_by_digest_r[digest_l]
                elems_moved.append(self.files_by_name_l[name])
            else:
                # print("< DELETED {}".format(name))
                self.files_by_name_l[name]['status'] = 'deleted'
                elems_deleted.append(self.files_by_name_l[name])
        return (elems_moved, elems_deleted)
