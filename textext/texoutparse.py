"""
Parser for LaTeX log files.

https://github.com/inakleinbottle/texoutparse

published under the

MIT License

Copyright (c) 2019

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

END OF LICENSE

Adapted to be compatible with Python 2.7 by TexText developers
"""
import re
from collections import deque


class LogFileMessage(object):
    """
    Helper class for storing log file messages.

    Messages and attributes of the messages can be accessed and added using
    the item notation.
    """

    def __init__(self):
        self.info = {}
        self.context_lines = []

    def __str__(self):
        return '\n'.join(self.context_lines)

    def __getitem__(self, item):
        try:
            return self.info[item]
        except KeyError:
            raise KeyError('Item {item} was not found.', format(item=item))

    def __setitem__(self, key, value):
        self.info[key] = value


class _LineIterWrapper(object):
    """
    Wrapper around an iterable that allows peeking ahead to get context lines
    without consuming the iterator.
    """

    def __init__(self, iterable, ctx_lines):
        self.iterable = iter(iterable)
        self.cache = deque()
        self.ctx_lines = ctx_lines
        self.current = None

    def __next__(self):
        if self.cache:
            self.current = current = self.cache.popleft()
        else:
            self.current = current = next(self.iterable)
        return current

    def next(self):
        pass

    def __iter__(self):
        return self

    def get_context(self):
        pass


class LatexLogParser(object):
    """
    Parser for LaTeX Log files.

    An LatexLogParser object can parse the log file or output of and generate
    lists of errors, warnings, and bad boxes described in the log. Each error.
    warning, or bad box is stored as a LogFileMessage in the corresponding
    list.
    """

    error = re.compile(
            r"^(?:! ((?:La|pdf)TeX|Package|Class)(?: (\w+))? [eE]rror(?: \(([\\]?\w+)\))?: (.*)|! (.*))"
            )
    warning = re.compile(
            r"^((?:La|pdf)TeX|Package|Class)(?: (\w+))? [wW]arning(?: \(([\\]?\w+)\))?: (.*)"
            )

    info = re.compile(
            r"^((?:La|pdf)TeX|Package|Class)(?: (\w+))? [iI]nfo(?: \(([\\]?\w+)\))?: (.*)"
            )
    badbox = re.compile(
            r"^(Over|Under)full "
            r"\\([hv])box "
            r"\((?:badness (\d+)|(\d+(?:\.\d+)?pt) too \w+)\) (?:"
            r"(?:(?:in paragraph|in alignment|detected) "
            r"(?:at lines (\d+)--(\d+)|at line (\d+)))"
            r"|(?:has occurred while [\\]output is active [\[](\d+)?[\]]))"
            )
    missing_ref = re.compile(
        r"^LaTeX Warning: (Citation|Reference) `([^']+)' on page (\d+) undefined on input line (\d+)\."
    )

    def __init__(self, context_lines=2):
        self.warnings = []
        self.errors = []
        self.badboxes = []
        self.missing_refs = []
        self.context_lines = context_lines

    def __str__(self):
        return "Errors: {len_err}, Warnings: {len_warn},  Badboxes: {len_bb}".format(
            len_err=len(self.errors), len_warn=len(self.warnings), len_bb=len(self.badboxes))

    def process(self, lines):
        """
        Process the lines of a logfile to produce a report.

        Steps through each non-empty line and passes it to the process_line
        function.

        :param lines: Iterable over lines of log.
        """
        pass

    def process_line(self, line):
        """
        Process a line in the log file and delegate to correct handler.

        Tests in turn matches to the badbox regex, warning regex, and
        then error regex. Once a match is found, the corresponding
        process function is called its result returned.

        :param line: Line to process
        :returns: LogFileMessage object or None
        """
        pass

    def process_badbox(self, match):
        """
        Process a badbox regex match and return the log message object.

        :param match: regex match object to process
        :return: LogFileMessage object
        """
        pass

    def process_warning(self, match):
        """
        Process a warning regex match and return the log message object.

        :param match: regex match object to process
        :return: LogFileMessage object
        """
        pass

    def process_error(self, match):
        """
        Process a warning regex match and return the log message object.

        :param match: regex match object to process
        :return: LogFileMessage object
        """
        pass

    def process_missing_ref(self, match):
        """
        Process a missing reference regex match and return log message object.

        :param match: regex match object to process
        :return: LogFileMessage object.
        """
        pass
