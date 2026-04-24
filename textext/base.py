"""
This file is part of TexText, an extension for the vector
illustration program Inkscape.

Copyright (c) 2006-2025 TexText developers.

TexText is released under the 3-Clause BSD license. See
file LICENSE.txt or go to https://github.com/textext/textext
for full license details.
"""
from __future__ import print_function
import hashlib
import logging
import logging.handlers
import math
import re
import os
import platform
import sys
import uuid
from io import open # ToDo: For open utf8, remove when Python 2 support is skipped

from .requirements_check import defaults, set_logging_levels, TexTextRequirementsChecker
from .utility import ChangeToTemporaryDirectory, CycleBufferHandler, MyLogger, NestedLoggingGuard, Settings, Cache, \
    exec_command, version_greater_or_equal_than
from .errors import *

with open(os.path.join(os.path.dirname(__file__), "VERSION")) as version_file:
    __version__ = version_file.readline().strip()
__docformat__ = "restructuredtext en"

EXIT_CODE_OK = 0
EXIT_CODE_EXPECTED_ERROR = 1
EXIT_CODE_UNEXPECTED_ERROR = 60

# There are two channels `file_log_channel` and `user_log_channel`
# `file_log_channel` dumps detailed log to a file
# `user_log_channel` accumulates log messages to show them to user via .show_messages() function
#
set_logging_levels()
logging.setLoggerClass(MyLogger)
__logger = logging.getLogger('TexText')
logger = NestedLoggingGuard(__logger)
__logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('[%(asctime)s][%(levelname)8s]: %(message)s          //  %(filename)s:%(lineno)-5d')

# First install the user logger so in case anything fails with the file logger
# we have at least some information in the abort dialog
# Contributed by Thermi@github.com
user_formatter = logging.Formatter('[%(name)s][%(levelname)6s]: %(message)s')
user_log_channel = CycleBufferHandler(capacity=1024)  # store up to 1024 messages
user_log_channel.setLevel(logging.DEBUG)
user_log_channel.setFormatter(user_formatter)
__logger.addHandler(user_log_channel)

# Now we try to install the file logger.
LOG_LOCATION = os.path.join(defaults.textext_logfile_path)
if not os.path.isdir(LOG_LOCATION):
    os.makedirs(LOG_LOCATION)
LOG_FILENAME = os.path.join(LOG_LOCATION, "textext.log") # ToDo: When not writable continue but give a message somewhere
file_log_channel = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                                        maxBytes=500 * 1024,  # up to 500 kB
                                                        backupCount=2,  # up to two log files
                                                        encoding="utf-8"
                                                        )
file_log_channel.setLevel(logging.NOTSET)
file_log_channel.setFormatter(log_formatter)
__logger.addHandler(file_log_channel)

import inkex
import inkex.command as ixc
from lxml import etree

TEXTEXT_NS = u"http://www.iki.fi/pav/software/textext/"
SVG_NS = u"http://www.w3.org/2000/svg"
XLINK_NS = u"http://www.w3.org/1999/xlink"

ID_PREFIX = "textext-"

NSS = {
    u'textext': TEXTEXT_NS,
    u'svg': SVG_NS,
    u'xlink': XLINK_NS,
}


# ------------------------------------------------------------------------------
# Inkscape plugin functionality
# ------------------------------------------------------------------------------

class TexText(inkex.EffectExtension):

    DEFAULT_ALIGNMENT = "middle center"
    DEFAULT_TEXCMD = "pdflatex"

    def __init__(self):

        self.config = Settings(directory=defaults.textext_config_path)
        self.cache = Cache(directory=defaults.textext_config_path)
        previous_exit_code = self.cache.get("previous_exit_code", None)

        if previous_exit_code is None:
            logging.disable(logging.NOTSET)
            logger.debug("First run of TexText. Enforcing DEBUG mode.")
        elif previous_exit_code == EXIT_CODE_OK:
            logging.disable(logging.CRITICAL)
        elif previous_exit_code == EXIT_CODE_UNEXPECTED_ERROR:
            logging.disable(logging.NOTSET)
            logger.debug("Enforcing DEBUG mode due to previous exit code `%d`" % previous_exit_code)
        else:
            logging.disable(logging.DEBUG)

        logger.debug("TexText initialized")
        with open(__file__, "rb") as fhl:
            logger.debug("TexText version = %s (md5sum = %s)" %
                         (repr(__version__), hashlib.md5(fhl.read()).hexdigest())
                         )
        logger.debug("platform.system() = %s" % repr(platform.system()))
        logger.debug("platform.release() = %s" % repr(platform.release()))
        logger.debug("platform.version() = %s" % repr(platform.version()))

        logger.debug("platform.machine() = %s" % repr(platform.machine()))
        logger.debug("platform.uname() = %s" % repr(platform.uname()))
        logger.debug("platform.mac_ver() = %s" % repr(platform.mac_ver()))

        logger.debug("sys.executable = %s" % repr(sys.executable))
        logger.debug("sys.version = %s" % repr(sys.version))
        logger.debug("os.environ = %s" % repr(os.environ))

        self.requirements_checker = TexTextRequirementsChecker(logger, self.config)

        if previous_exit_code == EXIT_CODE_OK and "requirements_checker" in self.cache.values:
            self.requirements_checker.inkscape_executable = self.cache["requirements_checker"][
                "inkscape_executable"]
            self.requirements_checker.available_tex_to_pdf_converters = self.cache["requirements_checker"][
                "available_tex_to_pdf_converters"]
            self.requirements_checker.available_pdf_to_svg_converters = self.cache["requirements_checker"][
                "available_pdf_to_svg_converters"]
        else:
            if self.requirements_checker.check() == False:
                raise TexTextFatalError("TexText requirements are not met. "
                                        "Please follow instructions "
                                        "https://textext.github.io/textext/")
            else:
                self.cache["requirements_checker"] = {
                    "inkscape_executable": self.requirements_checker.inkscape_executable,
                    "available_tex_to_pdf_converters": self.requirements_checker.available_tex_to_pdf_converters,
                    "available_pdf_to_svg_converters": self.requirements_checker.available_pdf_to_svg_converters,
                }

        super(TexText, self).__init__()

        self.arg_parser.add_argument(
            "--text",
            type=str,
            default=None)

        self.arg_parser.add_argument(
            "--preamble-file",
            type=str,
            default=self.config.get('preamble', "default_packages.tex"))

        self.arg_parser.add_argument(
            "--scale-factor",
            type=float,
            default=self.config.get('scale', 1.0)
        )

        self.arg_parser.add_argument(
            "--alignment",
            type=str,
            default=self.DEFAULT_ALIGNMENT
        )

        self.arg_parser.add_argument(
            "--recompile-all",
            action="store_true"
        )

        self.arg_parser.add_argument(
            "--tex_command",
            type=str,
            default=self.DEFAULT_TEXCMD
        )

    def _recompile_all(self):
        """
        Mutate ``self.svg`` to recompile all textext entries.
        This can be invoked from command-line as::

            python3 /path/to/textext/__main__.py --recompile-all        > edited.svg < original.svg
            python3 /path/to/textext/__main__.py --recompile-all --output edited.svg < original.svg

        In the first form ``edited.svg`` must not be the same as ``original.svg``,
        in the second form it is probably fine (although do make a backup).
        """
        pass

    def effect(self):
        """Perform the effect: create/modify TexText objects"""
        pass

    @staticmethod
    def find_all_textext_nodes(svg):
        # svg: has the same type as self.svg
        pass


    def preview_convert(self, text, preamble_file, image_setter, tex_command, white_bg):
        """
        Generates a preview PNG of the LaTeX output using the selected converter.

        :param text:
        :param preamble_file:
        :param image_setter: A callback to execute with the file path of the generated PNG
        :param tex_command: Command for tex -> pdf
        :param (bool) white_bg: set background to white if True
        """
        pass

    def _do_convert_one(self, text: str, preamble_file, user_scale_factor, alignment, tex_command):
        """
        Does the conversion using the selected converter.
        See documentation in do_convert for more details.
        """
        pass

    def _add_new_node(self, tt_node, user_scale_factor):
        pass

    def _replace_node(self, old_svg_ele, tt_node, user_scale_factor, alignment, original_scale):
        pass

    def do_convert(self, text, preamble_file, user_scale_factor, old_svg_ele, alignment, tex_command,
                   original_scale=None):
        """
        Does the conversion using the selected converter.

        :param text:
        :param preamble_file:
        :param user_scale_factor:
        :param old_svg_ele:
        :param alignment:
        :param tex_command: The tex command to be used for tex -> pdf ("pdflatex", "xelatex", "lualatex")
        :param original_scale Scale factor of old node
        """
        pass

    def get_old(self):
        """
        Dig out LaTeX code and name of preamble file from old
        TexText-generated objects.

        :return: (old_svg_ele, latex_text, preamble_file_name, scale)
        :rtype: (TexTextElement, str, str, float, bool)
        """
        pass

    def replace_node(self, old_node, new_node):
        """
        Replace an XML node old_node with new_node.
        This is only ever called from _replace_node. The parent is responsible
        for positioning the node correctly.
        """
        pass

    @staticmethod
    def copy_style(old_node, new_node):
        # ToDo: Implement this later depending on the choice of the user (keep Inkscape colors vs. Tex colors)
        pass


class TexToPdfConverter:
    """
    Base class for Latex -> SVG converters
    """
    DEFAULT_DOCUMENT_CLASS=r"\documentclass{article}"
    DOCUMENT_TEMPLATE = r"""
    %s
    \pagestyle{empty}
    \begin{document}
    %s
    \end{document}
    """

    LATEX_OPTIONS = ['-interaction=nonstopmode',
                     '-halt-on-error']

    def __init__(self, checker):
        self.tmp_base = 'tmp'
        self.checker = checker  # type: requirements_check.TexTextRequirementsChecker
        
        # If a file with the name "LATEX_OPTIONS" exists in the textext plugin directory, we interpret each line 
        # in that file not starting with "#" as a separate option to be passed to the latex command.
        # This can be used to customize the latex command line options - if needed
        # (for example when choosing to add the -shell-escape option)
        self.latex_options_path = os.path.join(os.path.dirname(__file__), "LATEX_OPTIONS")
        if os.path.exists(self.latex_options_path):
            with open(self.latex_options_path, 'r') as f:
                # Remove lines starting with "#" and empty lines
                self.LATEX_OPTIONS = [option for option in
                                      [s.strip() for s in f.read().splitlines()] if option and not option.startswith("#")]

    # --- Internal
    def tmp(self, suffix):
        """
        Return a file name corresponding to given file suffix,
        and residing in the temporary directory.
        """
        pass

    def tex_to_pdf(self, tex_command, latex_text, preamble_file):
        """
        Create a PDF file from latex text
        """
        pass

    def typ_to_any(self, typst_command, typst_text, preamble_file, file_type):
        """
        Create a PDF file from latex text
        """
        pass

    def pdf_to_svg(self):
        """Convert the PDF file to a SVG file"""
        pass

    def pdf_to_png(self, white_bg):
        """Convert the PDF file to a PNG file"""
        pass

    def parse_pdf_log(self):
        """
        Strip down tex output to only the first error etc. and discard all the noise
        :return: string containing the error message and some context lines after it
        """
        pass


def _contains_document_class(preamble):
    """Return True if `preamble` contains a documentclass-like command.
    
    Also, checks and considers if the command is commented out or not.
    """
    pass


class TexTextElement(inkex.Group):
    tag_name = "g"

    def __init__(self, svg_filename, document_unit):
        """
        :param svg_filename: The name of the file containing the svg-snippet
        :param document_unit: String specifying the unit of the document into which the node is going
                              to be placed ("mm", "pt", ...)
        """
        super(TexTextElement, self).__init__()
        self._svg_to_textext_node(svg_filename, document_unit)

    @staticmethod
    def to_textext_node(node):
        """
        Mutate node.__class__ to TexTextElement if it is detected
        to be a TexText node.

        :return: whether the node is detected as a TexText node
        :rtype: bool
        """
        pass

    def _svg_to_textext_node(self, svg_filename, document_unit):
        pass

    @staticmethod
    def _expand_defs(root):
        pass

    def make_ids_unique(self):
        """
        PDF->SVG converters tend to use same ids.
        To avoid confusion between objects with same id from two or more TexText objects we replace
        auto-generated ids from the converter with random unique values
        """
        pass

    def get_jacobian_sqrt(self):
        pass

    def set_meta(self, key, value):
        pass

    def set_meta_text(self, value):
        pass

    def get_meta_text(self):
        pass

    def get_meta_alignment(self):
        pass

    def get_meta(self, key, default=None):
        pass

    def get_all_info(self):
        pass

    def align_to_node(self, ref_node, alignment, relative_scale):
        """
        Aligns the node represented by self to a reference node according to the settings defined by the user
        :param (TexTextElement) ref_node: Reference node subclassed from SvgElement to which self is going to be aligned
        :param (str) alignment: A 2-element string list defining the alignment
        :param (float) relative_scale: Scaling of the new node relative to the scale of the reference node
        """
        pass

    @staticmethod
    def _get_pos(x, y, w, h, alignment):
        """ Returns the alignment point of a frame according to the required defined in alignment

        :param x, y, w, h: Position of top left corner, width and height of the frame
        :param alignment: String describing the required alignment, e.g. "top left", "middle right", etc.
        """
        pass

    def is_colorized(self):
        """ Returns true if at least one element of the managed node contains a non-black fill or stroke color """
        pass


    def has_colorized_attribute(self):
        """ Returns true if at least one element of node contains a non-black fill or stroke attribute """
        pass

    def has_colorized_style(self):
        """ Returns true if at least one element of node contains a non-black fill or stroke style """
        pass

    def import_group_color_style(self, src_svg_ele):
        """
        Extracts the color relevant style attributes of src_svg_ele (of class TexTextElement) and
        applies them to all items  of self. Ensures that non color relevant style
        attributes are not overwritten.
        """
        pass

    def pure_hlines_to_paths(self):
        """ Transforms horizontal lines from strokes to paths

        This makes coloring in Inkscape easier later since all other elements are paths, too.
        The color can be set by selecting the fill color. Without this function one would
        need to pick horizontal lines manually and set their stroke color instead of the fill
        color. Applies to frac and sqrt commands.
        """
        pass

    def set_none_strokes_to_0pt(self):
        """
        Iterates over all elements of the node. For each element which has the style attribute
        "stroke" set to "none" a style attribute "stroke-width" with value "0" is added. This
        ensures that when colorizing the node later in inkscape by setting the node and
        stroke colors letters do not become bold (letters have "stroke" set to "none" but e.g.
        horizontal lines in fraction bars and square roots are only affected by stroke colors
        so for full colorization of a node you need to set the fill as well as the stroke color!).
        """
        pass
