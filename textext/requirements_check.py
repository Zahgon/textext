"""
This file is part of TexText, an extension for the vector
illustration program Inkscape.

Copyright (c) 2006-2025 TexText developers.

TexText is released under the 3-Clause BSD license. See
file LICENSE.txt or go to https://github.com/textext/textext
for full license details.

Classes for handling and checking of the dependencies required
to successfully run TexText.
"""
from abc import ABCMeta, abstractmethod
import logging
import os
import re
import subprocess
import sys

VERBOSE = 5
SUCCESS = 41
UNKNOWN = 42


class Defaults(object):
    __metaclass__ = ABCMeta

    # ToDo: Change to @property @abstractmethod when discarding Python 2.7 support
    @property
    @abstractmethod
    def os_name(self): pass

    @property
    @abstractmethod
    def console_colors(self): pass

    @property
    @abstractmethod
    def executable_names(self): pass

    @property
    @abstractmethod
    def inkscape_user_extensions_path(self): pass

    def inkscape_system_extensions_path(self, inkscape_exe_path):
        pass

    @property
    @abstractmethod
    def textext_config_path(self): pass

    @property
    @abstractmethod
    def textext_logfile_path(self): pass

    @property
    @abstractmethod
    def get_system_path(self): pass

    @staticmethod
    @abstractmethod
    def call_command(command, return_code=0): pass

    @property
    @abstractmethod
    def example_path(self): pass

    @property
    @abstractmethod
    def setup_script(self): pass

class LinuxDefaults(Defaults):
    os_name = "linux"
    console_colors = "always"
    executable_names = {"inkscape": ["inkscape"],
                        "pdflatex": ["pdflatex"],
                        "lualatex": ["lualatex"],
                        "xelatex": ["xelatex"],
                        "typst": ["typst"]
                        }

    @property
    def inkscape_user_extensions_path(self):
        pass

    @property
    def textext_config_path(self):
        pass

    @property
    def textext_logfile_path(self):
        pass

    def get_system_path(self):
        pass

    @staticmethod
    def call_command(command, return_code=0):
        pass

    @property
    def example_path(self):
        pass

    @property
    def setup_script(self):
        pass

class MacDefaults(LinuxDefaults):
    os_name = "macos"
    executable_names = {"inkscape": ["inkscape", "inkscape-bin"],
                        "pdflatex": ["pdflatex"],
                        "lualatex": ["lualatex"],
                        "xelatex": ["xelatex"],
                        "typst": ["typst"]
                        }

    def get_system_path(self):
        pass

    @property
    def inkscape_user_extensions_path(self):
        pass

    @property
    def textext_config_path(self):
        pass

    @property
    def textext_logfile_path(self):
        pass

    @property
    def example_path(self):
        pass

    @property
    def setup_script(self):
        pass


class WindowsDefaults(Defaults):

    os_name = "windows"
    console_colors = "never"
    executable_names = {"inkscape": ["inkscape.exe"],
                        "pdflatex": ["pdflatex.exe"],
                        "lualatex": ["lualatex.exe"],
                        "xelatex": ["xelatex.exe"],
                        "typst": ["typst.exe"]
                        }

    def __init__(self):
        super(WindowsDefaults, self)
        from .win_app_paths import get_non_syspath_dirs
        self._tweaked_syspath = get_non_syspath_dirs() + os.environ["PATH"].split(os.path.pathsep)

        # Windows 10 supports colored output since anniversary update (build 14393)
        # so we try to use it (it has to be enabled since it is always disabled by default!)
        try:
            wininfo = sys.getwindowsversion()
            if wininfo.major >= 10 and wininfo.build >= 14393:

                import ctypes as ct
                h_kernel32 = ct.windll.kernel32

                #  STD_OUTPUT_HANDLE = -11
                # -> https://docs.microsoft.com/en-us/windows/console/getstdhandle
                h_stdout = h_kernel32.GetStdHandle(-11)

                # ENABLE_PROCESSED_OUTPUT  | ENABLE_WRAP_AT_EOL_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING = 7
                # -> https://docs.microsoft.com/en-us/windows/console/setconsolemode
                result = h_kernel32.SetConsoleMode(h_stdout, 7)

                self.console_colors = "always"
        except (ImportError, AttributeError):
            pass

    @property
    def inkscape_user_extensions_path(self):
        pass

    @property
    def textext_config_path(self):
        pass

    @property
    def textext_logfile_path(self):
        pass

    def get_system_path(self):
        pass

    @staticmethod
    def call_command(command, return_code=0): # type: (List,Optional[int]) -> Tuple[str, str]
        # Ensure that command window does not pop up on Windows!
        pass

    @property
    def example_path(self):
        pass

    @property
    def setup_script(self):
        pass


class TexTextLogFormatter(logging.Formatter):

    enable_colors = False

    COLOR_RESET = "\033[0m"
    FG_DEFAULT = "\033[39m"
    FG_BLACK = "\033[30m"
    FG_RED = "\033[31m"
    FG_GREEN = "\033[32m"
    FG_YELLOW = "\033[33m"
    FG_BLUE = "\033[34m"
    FG_MAGENTA = "\033[35m"
    FG_CYAN = "\033[36m"
    FG_LIGHT_GRAY = "\033[37m"
    FG_DARK_GRAY = "\033[90m"
    FG_LIGHT_RED = "\033[91m"
    FG_LIGHT_GREEN = "\033[92m"
    FG_LIGHT_YELLOW = "\033[93m"
    FG_LIGHT_BLUE = "\033[94m"
    FG_LIGHT_MAGENTA = "\033[95m"
    FG_LIGHT_CYAN = "\033[96m"
    FG_WHITE = "\033[97m"

    BG_DEFAULT = "\033[49m"
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_LIGHT_GRAY = "\033[47m"
    BG_DARK_GRAY = "\033[100m"
    BG_LIGHT_RED = "\033[101m"
    BG_LIGHT_GREEN = "\033[102m"
    BG_LIGHT_YELLOW = "\033[103m"
    BG_LIGHT_BLUE = "\033[104m"
    BG_LIGHT_MAGENTA = "\033[105m"
    BG_LIGHT_CYAN = "\033[106m"
    BG_WHITE = "\033[107m"

    UNDERLINED = "\033[4m"

    LEVELS = [
        VERBOSE,  # 5
        logging.DEBUG,  # 10
        logging.INFO,  # 20
        logging.WARNING,  # 30
        logging.ERROR,  # 40
        SUCCESS,  # 41
        UNKNOWN,  # 42
        logging.CRITICAL  # 50
    ]
    NAMES = [
        "VERBOSE ",
        "DEBUG   ",
        "INFO    ",
        "WARNING ",
        "ERROR   ",
        "SUCCESS ",
        "UNKNOWN ",
        "CRITICAL"
    ]
    colors = [
        COLOR_RESET,  # VERBOSE
        COLOR_RESET,  # DEBUG
        BG_DEFAULT + FG_LIGHT_BLUE,  # INFO
        BG_DEFAULT + FG_YELLOW,  # WARNING
        BG_DEFAULT + FG_RED,  # ERROR
        BG_DEFAULT + FG_GREEN,  # SUCCESS
        BG_DEFAULT + FG_YELLOW,  # UNKNOWN
        BG_RED + FG_WHITE,  # CRITICAL
    ]

    @classmethod
    def get_levels(cls):
        return [x for x in zip(cls.LEVELS, cls.NAMES)]

    def format(self, record):
        pass


def set_logging_levels():
    for log_level, level_name in TexTextLogFormatter.get_levels():
        logging.addLevelName(log_level, level_name)


class TexTextRequirementsChecker(object):
    MINIMUM_REQUIRED_INKSCAPE_VERSION = "1.4.3"

    def __init__(self, logger, config):
        self.logger = logger
        self.config = config
        self.available_tex_to_pdf_converters = {}
        self.available_pdf_to_svg_converters = {}

        self.inkscape_prog_name = "inkscape"
        self.pdflatex_prog_name = "pdflatex"
        self.lualatex_prog_name = "lualatex"
        self.xelatex_prog_name = "xelatex"
        self.typst_prog_name = "typst"

        self.inkscape_executable = None

        self.pygtk_is_found = False
        self.tkinter_is_found = False

        pass

    def find_gtk3(self) -> bool:
        pass

    def find_tkinter(self) -> bool:
        pass

    def find_inkscape(self) -> bool:
        pass

    def find_executable(self, prog_name) -> str:
        # try value from config
        pass

    def _find_executable_in_path(self, prog_name) -> str:
        pass

    @staticmethod
    def check_executable(filename) -> bool:
        pass

    def check(self):

        pass


if sys.platform.startswith("win"):
    defaults = WindowsDefaults()
elif sys.platform.startswith("darwin"):
    defaults = MacDefaults()
else:
    defaults = LinuxDefaults()
