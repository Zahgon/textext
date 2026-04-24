"""
This file is part of TexText, an extension for the vector
illustration program Inkscape.

Copyright (c) 2006-2025 TexText developers.

TexText is released under the 3-Clause BSD license. See
file LICENSE.txt or go to https://github.com/textext/textext
for full license details.

Provides handlers for temp-dir management, logging, settings and
system command execution
"""
import contextlib
import json
import logging.handlers
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import re

from .errors import *
import sys


class ChangeDirectory(object):
    def __init__(self, dir):
        self.new_dir = dir
        self.old_dir = os.path.abspath(os.path.curdir)

    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.old_dir)


class TemporaryDirectory(object):
    """ Mimic tempfile.TemporaryDirectory from python3 """
    def __init__(self):
        self.dir_name = None

    def __enter__(self):
        self.dir_name = tempfile.mkdtemp("textext_")
        return self.dir_name

    def __exit__(self, exc_type, exc_val, exc_tb):

        def retry_with_chmod(func, path, exec_info):
            pass

        if self.dir_name:
            shutil.rmtree(self.dir_name, onerror=retry_with_chmod)


@contextlib.contextmanager
def ChangeToTemporaryDirectory():
    with TemporaryDirectory() as temp_dir:
        with ChangeDirectory(temp_dir):
            yield None


class MyLogger(logging.Logger):
    """
        Needs to produce correct line numbers
    """
    def findCaller(self, *args):
        pass


class NestedLoggingGuard(object):
    message_offset = 0
    message_indent = 2

    def __init__(self, _logger, lvl=None, message=None):
        self._logger = _logger
        self._level = lvl
        self._message = message
        if lvl is not None and message is not None:
            self._logger.log(self._level, " " * NestedLoggingGuard.message_offset + self._message)

    def __enter__(self):
        assert self._level is not None
        assert self._message is not None
        NestedLoggingGuard.message_offset += NestedLoggingGuard.message_indent

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._level is not None
        assert self._message is not None
        if exc_type is None:
            result = "done"
        else:
            result = "failed"
        NestedLoggingGuard.message_offset -= NestedLoggingGuard.message_indent

        def tmp1():  # this nesting needed to even number of stack frames in __enter__ and __exit__
            pass
        tmp1()

    def debug(self, message):
        pass

    def info(self, message):
        pass

    def error(self, message):
        pass

    def warning(self, message):
        pass

    def critical(self, message):
        pass

    def log(self, lvl, message):
        pass


class CycleBufferHandler(logging.handlers.BufferingHandler):

    def __init__(self, capacity):
        super(CycleBufferHandler, self).__init__(capacity)

    def emit(self, record):
        pass

    def show_messages(self):
        pass


class Settings(object):
    def __init__(self, basename="config.json", directory=None):
        if directory is None:
            directory = os.getcwd()
        else:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        self.values = {}
        self.directory = directory
        self.config_path = os.path.join(directory, basename)
        try:
            self.load()
        except ValueError as e:
            raise TexTextFatalError("Bad config `%s`: %s. Please fix it and re-run TexText." % (self.config_path, str(e)) )

    def load(self):
        pass

    def save(self):
        pass

    def get(self, key, default=None):
        pass

    def delete_file(self):
        pass

    def __getitem__(self, key):
        return self.values.get(key)

    def __setitem__(self, key, value):
        if value is not None:
            self.values[key] = value
        else:
            self.values.pop(key, None)


class Cache(Settings):
    def __init__(self, basename=".cache.json", directory=None):
        try:
            super(Cache, self).__init__(basename, directory)
        except TexTextFatalError:
            pass


class SuppressStream(object):
    """
    "Suppress stream output" context manager

    Effectively redirects output to /dev/null by switching fileno
    """

    def __init__(self, stream=sys.stderr):
        self.orig_stream_fileno = stream.fileno()

    def __enter__(self):
        self.orig_stream_dup = os.dup(self.orig_stream_fileno)
        self.devnull = open(os.devnull, 'w')
        os.dup2(self.devnull.fileno(), self.orig_stream_fileno)

    def __exit__(self, type, value, traceback):
        os.close(self.orig_stream_fileno)
        os.dup2(self.orig_stream_dup, self.orig_stream_fileno)
        os.close(self.orig_stream_dup)
        self.devnull.close()


def exec_command(cmd, ok_return_value=0):
    """
    Run given command, check return value, and return
    concatenated stdout and stderr.
    :param cmd: Command to execute
    :param ok_return_value: The expected return value after successful completion
    :raises: TexTextCommandNotFound, TexTextCommandFailed
    """

    try:
        # hides the command window for cli tools that are run (in Windows)
        info = None
        if PLATFORM == WINDOWS:
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = subprocess.SW_HIDE

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             startupinfo=info)
        out, err = p.communicate()
    except OSError as err:
        raise TexTextCommandNotFound("Command %s failed: %s" % (' '.join(cmd), err))

    if ok_return_value is not None and p.returncode != ok_return_value:
        raise TexTextCommandFailed(message="Command %s failed (code %d)" % (' '.join(cmd), p.returncode),
                                   return_code=p.returncode,
                                   stdout=out,
                                   stderr=err)
    return out + err


def version_greater_or_equal_than(version_str, other_version_str):
    """ Checks if a version number is >= than another version number

    Version numbers are passed as strings and must be of type "N.M.Rarb" where N, M, R
    are non negative decimal numbers < 1000 and arb is an arbitrary string.
    For example, "1.2.3" or "1.2.3dev" or "1.2.3-dev" or "1.2.3 dev" are valid version strings.

    Returns:
        True if the version number is equal or greater then the other version number,
        otherwise false

    """
    def ver_str_to_float(ver_str):
        """ Parse version string and returns it as a floating point value

        Returns The version string as floating point number for easy comparison
        (minor version and relase number padded with zeros). E.g. "1.23.4dev" -> 1.023004.
        If conversion fails returns NaN.

        """
        m = re.search(r"(\d+).(\d+).(\d+)[-\w]*", ver_str)
        if m is not None:
            ver_maj, ver_min, ver_rel = m.groups()
            return float("{}.{:0>3}{:0>3}".format(ver_maj, ver_min, ver_rel))
        else:
            return float("nan")

    return ver_str_to_float(version_str) >= ver_str_to_float(other_version_str)


MAC = "Darwin"
WINDOWS = "Windows"
PLATFORM = platform.system()