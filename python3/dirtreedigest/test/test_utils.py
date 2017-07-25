
import pytest
import dirtreedigest.utils as dtutils

@pytest.mark.parametrize(
    ('path', 'rval'), [
        ('C:\\', 'C:/'),
        ('C:\\test', 'C:/test'),
    ])
def test_unixify_path(path, rval):
    assert dtutils.unixify_path(path) == rval

@pytest.mark.parametrize(
    ('path', 'rval'), [
        ('C:/', ('C:', '/')),
        ('C:/test', ('C:', '/test')),
    ])
def test_split_win_drive(path, rval):
    assert dtutils.split_win_drive(path) == rval

@pytest.mark.parametrize(
    ('path', 'rval'), [
        ('//remote/', ('//remote', '/')),
        ('//remote/test', ('//remote', '/test')),
        ('//remote/test/a', ('//remote', '/test/a')),
    ])
def test_split_net_drive(path, rval):
    assert dtutils.split_net_drive(path) == rval

@pytest.mark.parametrize(
    ('root', 'elem', 'rval'), [
        ('C:/', 'C:/test/a', 'test/a'),
        ('C:',  'C:/test/a', 'test/a'),
        ('C:/test', 'C:/test/a', 'a'),
        ('/', '/test/a', 'test/a'),
        ('/', '/test/a', 'test/a'),
        ('/a', '/b/a', 'b/a'),
        ('//remote', '//remote/a', 'a'),
        ('//remote/', '//remote/a', 'a'),
    ])
def test_get_relative_path(root, elem, rval):
    assert dtutils.get_relative_path(root, elem) == rval

@pytest.mark.parametrize(
    ('root', 'elem', 'patterns', 'ignorecase', 'rval'), [
        ('//remote/', '//remote/a', ['a'], False, True),
        ('C:/', 'C:/test/a', ['a'], False, False),
        ('C:/', 'C:/test/a', ['test/a'], False, True),
        ('C:/', 'C:/test/A', ['test/a'], False, False),
        ('C:/', 'C:/test/A', ['test/a'], True, True),
        ('C:/', 'C:/test/A', [], True, False),
    ])
def test_elem_is_matched(root, elem, patterns, ignorecase, rval):
    re_pats = dtutils.compile_patterns(patterns, ignorecase)
    assert dtutils.elem_is_matched(root, elem, re_pats) == rval

