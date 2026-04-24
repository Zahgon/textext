"""
This file is part of TexText, an extension for the vector
illustration program Inkscape.

Copyright (c) 2006-2025 TexText developers.

TexText is released under the 3-Clause BSD license. See
file LICENSE.txt or go to https://github.com/textext/textext
for full license details.

This is the GUI part of TexText, handling several more or less
sophisticated dialog windows depending on the installed tools.

It is used uniformly from base.py via the ask method of the
AskText class depending on the available GUI framework
(TkInter or GTK3).
"""

DEBUG = False
debug_text = r"""$
\left(
   \begin{array}{ccc}
     a_{11} & \cdots & a_{1n} \\
     \vdots & \ddots & \vdots \\
     a_{m1} & \cdots & a_{mn}
   \end{array}
\right)
$"""

WINDOW_TITLE = "Enter LaTeX Formula - TexText"

import os
import sys
import warnings
import traceback
from .errors import TexTextCommandFailed
from textext.utility import SuppressStream


class AskText(object):
    """GUI for editing TexText objects"""

    ALIGNMENT_LABELS = ["top left", "top center", "top right",
                        "middle left", "middle center", "middle right",
                        "bottom left", "bottom center", "bottom right"]
    DEFAULT_WORDWRAP = False
    DEFAULT_SHOWLINENUMBERS = True
    DEFAULT_AUTOINDENT = True
    DEFAULT_INSERTSPACES = True
    DEFAULT_TABWIDTH = 4
    DEFAULT_FONTSIZE = 11
    DEFAULT_NEW_NODE_CONTENT = "Empty"
    DEFAULT_CLOSE_SHORTCUT = "Escape"
    DEFAULT_CONFIRM_CLOSE = True
    DEFAULT_PREVIEW_WHITE_BACKGROUND = False
    FONT_SIZE = [11, 12, 14, 16]
    NEW_NODE_CONTENT = ["Empty", "InlineMath", "DisplayMath"]
    CLOSE_SHORTCUT = ["Escape", "CtrlQ", "None"]

    def __init__(self, version_str, text, preamble_file, global_scale_factor, current_scale_factor, current_alignment,
                 current_texcmd, tex_commands, gui_config):
        self.TEX_COMMANDS = tex_commands
        if len(text) > 0:
            self.text = text
        else:
            if DEBUG:
                self.text = debug_text
            else:
                self.text = ""

        self.textext_version = version_str
        self.callback = None
        self.global_scale_factor = global_scale_factor
        self.current_scale_factor = current_scale_factor
        self.current_alignment = current_alignment

        if current_texcmd in self.TEX_COMMANDS:
            self.current_texcmd = current_texcmd
        else:
            self.current_texcmd = self.TEX_COMMANDS[0]
        self.using_tex = self.current_texcmd != "typst"

        self.preamble_file = preamble_file

        # TexText < 1.10 did not use preamble files for typst and just stored
        # the default_packages.tex. Hence, we have to correct this here.
        if not self.using_tex and "default_packages.tex" in self.preamble_file:
            self.preamble_file = "default_preamble_typst.typ"

        if self.using_tex:
            self.latex_default_preamble_file = self.preamble_file
            self.typst_default_preamble_file = "default_preamble_typst.typ"
        else:
            self.latex_default_preamble_file = "default_packages.tex"
            self.typst_default_preamble_file = self.preamble_file

        self._preamble_widget = None
        self._scale = None
        self._gui_config = gui_config
        self._source_buffer = None
        self._ok_button = None
        self._cancel_button = None
        self._window = None

    def ask(self, callback, preview_callback=None):
        """
        Present the GUI for entering LaTeX code and setting some options
        :param callback: A callback function (basically, what to do with the values from the GUI)
        :param preview_callback: A callback function to run to create a preview rendering
        """
        raise NotImplementedError()

    def show_error_dialog(self, title, message_text, exception):
        """
        Presents an error dialog

        :param parent: Parent window
        :param title: Error title text
        :param message_text: Message text to be displayed
        :param exception: Exception thrown
        """
        raise NotImplementedError()

    @staticmethod
    def cb_cancel(widget=None, data=None):
        """Callback for Cancel button"""
        raise NotImplementedError()

    def cb_ok(self, widget=None, data=None):
        """Callback for OK / Save button"""
        raise NotImplementedError()

    def scale_factor_after_loading(self):
        """
        The slider's initial scale factor:
         Either the previously saved value or the global scale factor or a default of 1.0 if the extension
         runs for the first time.

        :return: Initial scale factor for the slider
        """
        pass


def load_asktext_tk():
    """
    Returns a subclass of AskText that uses TK.

    May raise ImportError if TK is not installed.
    """
    pass


def load_asktext_gtk(use_gtk_source=None):
    """
    Returns a subclass of AskText that uses GTK.

    May raise ImportError, TypeError, ValueError.

    :param use_gtk_source: If None, try to use GTKSourceView, if unavailable then use fallback.
    If True, raise error if not available. If False, never use.
    """
    pass
