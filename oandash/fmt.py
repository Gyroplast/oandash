#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LICENSING INFORMATION
#
#    This file is part of oandash.
#
#    oandash is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    oandash is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with oandash.  If not, see <http://www.gnu.org/licenses/>.

from colorama import Fore, Back, Style

def reindent(s, numSpaces=0):
    s = s.split('\n')
    s = [(numSpaces * ' ') + line.lstrip() for line in s]
    s = '\n'.join(s)
    return s

def help(help_data):
    s = "Help for command: %s%s%s\n\n" % (Style.BRIGHT, help_data['cmd'], Style.NORMAL)
    s += "%sUsage%s: %s %s\n\n%s" % (Style.BRIGHT, Style.NORMAL, help_data['cmd'], help_data['args'], reindent(help_data['desc'], 4))
    return s

def balance(val):
    try:
        val = float(val)
    except ValueError:
        return "NaN"

    if val < 0:
        return "{0}{1:,.2f}{2}".format(Fore.RED, val, Fore.RESET)
    elif val > 0:
        return "{0}{1:,.2f}{2}".format(Fore.GREEN, val, Fore.RESET)
    else:
        return "{0:,.2f}".format(val)
