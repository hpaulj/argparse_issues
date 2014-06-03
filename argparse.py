# Author: Steven J. Bethard <steven.bethard@gmail.com>.

"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

    - handles both optional and positional arguments
    - produces highly informative usage messages
    - supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file::

    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')
    parser.add_argument(
        'integers', metavar='int', nargs='+', type=int,
        help='an integer to be summed')
    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()
    args.log.write('%s' % sum(args.integers))
    args.log.close()

The module contains the following public classes:

    - ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    - ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    - FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    - Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    - HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
        ArgumentDefaultsHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default,
        RawDescriptionHelpFormatter and RawTextHelpFormatter tell the parser
        not to change the formatting for help text, and
        ArgumentDefaultsHelpFormatter adds information about argument defaults
        to the help.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""

__version__ = '1.1'
__all__ = [
    'ArgumentParser',
    'ArgumentError',
    'ArgumentTypeError',
    'FileType',
    'HelpFormatter',
    'ArgumentDefaultsHelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'MetavarTypeHelpFormatter',
    'CompactHelpFormatter',
    'MultiGroupHelpFormatter',
    'Namespace',
    'Action',
    'ONE_OR_MORE',
    'OPTIONAL',
    'PARSER',
    'REMAINDER',
    'SUPPRESS',
    'ZERO_OR_MORE',
]


import collections as _collections
import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _, ngettext
from functools import partial as _partial

SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'
_UNRECOGNIZED_ARGS_ATTR = '_unrecognized_args'

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            arg_strings.append('%s=%r' % (name, value))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)

class _DelayedValue(_partial):
    """Subclass this to reliably identify a particular use of partial
    """
    pass

def _is_mnrep(nargs):
    # test for are like string, {n,m}
    # return valid nargs, or False if not valid
    # it also converts a (m,n) tuple to equivalent {m,n} string
    # could be action method
    if nargs is None:
        return False
    if isinstance(nargs, int):
        return False
    if isinstance(nargs, tuple):
        if len(nargs)==2:
            nargs = '{%s,%s}'%nargs
            nargs = nargs.replace('None','')
        else:
            msg = _('nargs tuple requires 2 integers')
            raise ValueError(msg)
    m = _re.match('{(\d*),?(\d*)}',nargs)
    if m:
        try:
            x = _re.compile('[-A]%s'%nargs)
            return nargs
        except _re.error as e:
            raise ValueError(str(e))
    else:
        return False

def _format_choices(choices, expand=False, summarize=None):
    # issue 16468
    # consolidate the choices formatting in one place
    # use formatting as before
    # unless choices is not iterable
    # in which case the repr()
    # could make this an Action method
    # another thing to use is the metavar
    if hasattr(choices, '__contains__'):
        rep = repr(choices)
    else:
        msg = _('choices must support the in operator')
        raise AttributeError(msg)
    # or do ' ' in choices, which would raise
    # TypeError: argument of type 'instance' is not iterable
    try:
        choice_strs = [str(choice) for choice in choices]
        if summarize:
            n = len(choice_strs)
            if n>summarize:
                split = [6,2]
                if summarize<15:
                    split = [summarize//3,2]
                # should tweak this is n is close to 10
                ll = [choice_strs[i] for i in range(0, split[0])]
                ll += ['...']
                ll += [choice_strs[i] for i in range(n-split[1],n)]
                choice_strs = ll
        if expand:
            # expanded form used in help
            result = ', '.join(choice_strs)
        else:
            # compact form used in usage
            result = '{%s}' % ','.join(choice_strs)
            rep = rep.replace(' ', '')
    except TypeError:
        return rep
    return result

# ===============
# Formatting Help
# ===============

class HelpFormatter(object):
    """Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        # default setting for width
        if width is None:
            try:
                width = int(_os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2

        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = max_help_position
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._whitespace_matcher = _re.compile(r'\s+')
        self._long_break_matcher = _re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object):

        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            for func, args in self.items:
                func(*args)
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = '%*s%s:\n' % (current_indent, '', self.heading)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join([part
                        for part in part_strings
                        if part and part is not SUPPRESS])

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            format = self._format_actions_usage
            action_parts = format(optionals + positionals, groups)
            usage = ' '.join([prog]+action_parts)

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                opt_parts = format(optionals, groups)
                pos_parts = format(positionals, groups)

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line and line_len + 1 + len(part) > text_width:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent):]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # format the usage using the actions list. Where possible
        # format the groups that include those actions
        # The actions list has priority
        # This is a new version that formats the groups directly without
        # needing inserts, (most) cleanup, or parsing into parts
        parts = []
        i = 0
        # step through the actions list
        while i<len(actions):
            start = end = i
            action = actions[i]
            group_part = None
            for group in groups:
                if hasattr(group, 'no_usage') and group.no_usage:
                    continue
                # see if the following 'n' actions are part of a group
                if group._group_actions and action == group._group_actions[0]:
                    end = start + len(group._group_actions)
                    if actions[start:end] == group._group_actions:
                        group_part = self._format_group_usage(group)
                        if group_part:
                            parts += group_part
                        # could remove this group from further consideration
                        i = end
                    break
            if group_part is None:
                # this action is not part of a group, format it alone
                part = self._format_just_actions_usage([action])
                if part:
                    parts += part
                i += 1
        parts = [s for s in parts if s] # remove '' parts
        return parts

    def _format_group_usage(self, group):
        # format one group
        actions = group._group_actions
        parts = []

        parts += '(' if group.required else '['
        for action in actions:
            part = self._format_just_actions_usage([action])
            if part:
                part = _re.sub(r'^\[(.*)\]$', r'\1', part[0]) # remove 'optional'[]
                parts.append(part)
                parts.append(' | ')
        if len(parts)>1:
            parts[-1] = ')' if group.required else ']'
        else:
            # nothing added
            parts = []
        arg_parts = [''.join(parts)]

        def cleanup(text):
            # remove unnecessary ()
            text = _re.sub(r'^\(([^|]*)\)$', r'\1', text)
            return text
        arg_parts = [cleanup(t) for t in arg_parts]
        return arg_parts

    def _format_just_actions_usage(self, actions):
        # actions, without any group markings
        parts = []
        for action in actions:
            if action.help is SUPPRESS:
                pass
            elif not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                part = action._format_args(default)
                parts.append(part)
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = '%s' % option_string

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = action._format_args(default)
                    part = '%s %s' % (option_string, args_string)

                # make it look optional if it's not required
                if not action.required:
                    part = '[%s]' % part
                parts.append(part)
        return parts

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        text_width = self._width - self._current_indent
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar = action._metavar_formatter(default)()
            return metavar
        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = action._format_args(default)
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], '__name__'):
                params[name] = params[name].__name__
        if params.get('choices') is not None:
            choices_str = _format_choices(params['choices'], expand=True)
            params['choices'] = choices_str
        return self._get_help_string(action) % params

    def _iter_indented_subactions(self, action):
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            yield from get_subactions()
            self._dedent()

    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.fill(text, width, initial_indent=indent,
                                           subsequent_indent=indent)

    def _get_help_string(self, action):
        return action.help

    def _get_default_metavar_for_optional(self, action):
        return action.dest.upper()

    def _get_default_metavar_for_positional(self, action):
        return action.dest


class RawDescriptionHelpFormatter(HelpFormatter):
    """Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text, width, indent):
        return ''.join(indent + line for line in text.splitlines(keepends=True))


class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    """Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text, width):
        return text.splitlines()


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not SUPPRESS:
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


class MetavarTypeHelpFormatter(HelpFormatter):
    """Help message formatter which uses the argument 'type' as the default
    metavar value (instead of the argument 'dest')

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_default_metavar_for_optional(self, action):
        return action.type.__name__

    def _get_default_metavar_for_positional(self, action):
        return action.type.__name__

class CompactHelpFormatter(HelpFormatter):
    """Help message formatter which uses a more compact optionals help line
    Some users complain about the long help line when there are many option_strings
    This produces
        -b/--boo BOO
    instead of
        -b Boo  --boo BOO

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            return action._metavar_formatter(default)()
            """
            if len(metavar)>1:
                metavar = action.get_name()
                # return _format_tuple_metavar(action, self)
            else:
                metavar = metavar[0]
            return metavar
            """
        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s/--long
            if action.nargs == 0:
                parts.append(action.get_name())

            # if the Optional takes a value, format is:
            #    -s/--long ARGS
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = action._format_args(default)
                option_string = action.get_name()
                parts.append('%s %s' % (option_string, args_string))
            return ', '.join(parts)

# from multigroup, issue 10984
class MultiGroupHelpFormatter(HelpFormatter):
    """Help message formatter that handles overlapping mutually exclusive
    groups.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.

    This formats all the groups, even if they share actions, or the actions
    do not occur in the other in which they were defined (in parse._actions)
    Thus an action may appear in more than one group
    Groups are presented in an order that preserves the order of positionals
    """

    def _format_usage(self, usage, actions, groups, prefix):
        #
        if prefix is None:
            prefix = _('usage: ')

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)
            #optionals = [action for action in actions if action.option_strings]
            #positionals = [action for action in actions if not action.option_strings]

            # build full usage string
            format = self._format_actions_usage
            # (opt_parts, pos_parts) = format(optionals + positionals, groups)
            (opt_parts, arg_parts, pos_parts) = format(actions, groups)
            all_parts = opt_parts + arg_parts + pos_parts

            usage = ' '.join([prog]+all_parts)
            opt_parts = opt_parts + arg_parts # for now join these

            # the rest is the same as in the parent formatter
            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:
                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line and line_len + 1 + len(part) > text_width:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent):]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # usage will list
        # optionals that are not in a group
        # actions in groups, with possible repetitions
        # positionals that not in a group
        # It orders groups with positionals to preserved the parsing order
        actions = actions[:] # work with copy, not original
        groups = self._group_sort(actions, groups)
        seen_actions = set()
        arg_parts = []
        for group in groups:
            #gactions = group._group_actions
            if True:
                group_parts, gactions = self._format_group_usage(group)
                seen_actions.update(gactions)
                arg_parts.extend(group_parts)

        # now format all remaining actions
        for act in seen_actions:
            try:
                actions.remove(act)
            except ValueError:
                pass
        # find optionals and positionals in the remaining actions list
        # i.e. ones that are not in any group
        optionals = [action for action in actions if action.option_strings]
        positionals = [action for action in actions if not action.option_strings]

        opt_parts = self._format_just_actions_usage(optionals)
        #arg_parts = parts + arg_parts

        pos_parts = self._format_just_actions_usage(positionals)
        # keep pos_parts separate, so they can be handled separately in long lines
        return (opt_parts, arg_parts, pos_parts)

    def _group_sort(self, actions, groups):
        # sort groups by order of positionals, if any
        from operator import itemgetter
        if len(groups)==0:
            return groups
        optionals = [action for action in actions if action.option_strings]
        positionals = [action for action in actions if not action.option_strings]

        # create a sort key, based on position of action in actions
        posdex = [-1]*len(groups)
        noInGroups = set(positionals)
        for i,group in enumerate(groups):
            for action in group._group_actions:
                if action in positionals:
                    posdex[i] = positionals.index(action)
                    noInGroups.discard(action)
        sortGroups = groups[:]
        # actions not found in any group are put in their own tempory groups
        samplegroup = group
        for action in noInGroups:
            g = _copy.copy(samplegroup)
            g.required = action.required
            g._group_actions = [action]
            sortGroups.append(g)
            posdex.append(positionals.index(action))

        sortGroups = sorted(zip(sortGroups,posdex), key=itemgetter(1))
        sortGroups = [i[0] for i in sortGroups]
        return sortGroups

    # need to sort out the []() for nested groups
    # when do these just mark groups, what does it mean to be be 'required' when nested
    # need to collect actions when nesting

    def _format_group_usage(self, group):
        # format one group
        joiner = getattr(group, 'joiner', ' | ')
        seen_actions = set()
        actions = group._group_actions
        parts = []

        parts += '(' if group.required else '['
        for action in actions:
            if isinstance(action, _NestingGroup):
                part, gactions = self._format_group_usage(action)
                seen_actions.update(gactions)
                part = part[0]
            else:
                part = self._format_just_actions_usage([action])
                part = _re.sub(r'^\[(.*)\]$', r'\1', part[0]) # remove 'optional'[]
                seen_actions.add(action)
            if part:
                parts.append(part)
                parts.append(joiner)
        if len(parts)>1:
            parts[-1] = ')' if group.required else ']'
        else:
            # nothing added
            parts = []
        arg_parts = [''.join(parts)]

        def cleanup(text):
            # remove unnecessary ()
            pat = r'^\(([^(%s)]*)\)$'%joiner # is this robust enough?
            text = _re.sub(pat, r'\1', text)
            return text
        arg_parts = [cleanup(t) for t in arg_parts]
        return arg_parts, seen_actions

# =====================
# Options and Arguments
# =====================

def _get_action_name(argument):
    return None if argument is None else argument.get_name()

class ArgumentError(Exception):
    """An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument, message):
        self.argument_name = None if argument is None else argument.get_name()
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)


class ArgumentTypeError(Exception):
    """An error from trying to convert a command line string to a type."""
    pass


# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Information about how to convert command line strings to Python objects.

    Action objects are used by an ArgumentParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - option_strings -- A list of command-line option strings which
            should be associated with this action.

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - const -- The value to be produced if the option is specified and the
            option uses an action that takes no values.

        - default -- The value to be produced if the option is not specified.

        - type -- A callable that accepts a single string argument, and
            returns the converted value.  The standard Python types str, int,
            float, and complex are useful examples of such callables.  If None,
            str is used.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - required -- True if the action must always be specified at the
            command line. This is only meaningful for optional command-line
            arguments.

        - help -- The help string describing the argument.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace, values, option_string=None):
        raise NotImplementedError(_('.__call__() not defined'))

    def get_name(self, metavar=None):
        """
        Action name, used in error messages
        can also be used by help line formatter
        """
        # optional
        if self.option_strings:
            return  '/'.join(self.option_strings)
        # positional
        if metavar is None:
            # caller may over over ride metavar
            metavar = self.metavar
        if metavar not in (None, SUPPRESS):
            if isinstance(metavar, tuple):
                # use a method to reduce a tuple to a string
                return self._format_tuple_metavar() # 14704
            else:
                return metavar
        elif self.dest not in (None, SUPPRESS):
            return self.dest
        elif hasattr(self, 'name'):  # action.name
            return self.name()
        else:
            return None

    def _get_nargs_pattern(self):
        # translate nargs to patterns used by parser
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = self.nargs

        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '(-*A-*)'

        # allow zero or one arguments
        elif nargs == OPTIONAL:
            nargs_pattern = '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == ZERO_OR_MORE:
            nargs_pattern = '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == ONE_OR_MORE:
            nargs_pattern = '(-*A[A-]*)'

        # allow any number of options or arguments
        elif nargs == REMAINDER:
            nargs_pattern = '([-AO]*)'

        # allow one argument followed by any number of options or arguments
        elif nargs == PARSER:
            nargs_pattern = '(-*A[-AO]*)'

        # n to m arguments, nargs is re like {n,m}
        elif _is_mnrep(nargs):
            nargs_pattern = '([-A]%s)'%nargs

        elif nargs == SUPPRESS: # 14191
            nargs_pattern = '(-*-*)'

        # all others should be integers
        else:
            if not isinstance(self.nargs, int):
                msg = _('nargs %r not integer or valid string'%(self.nargs))
                raise ValueError(msg)
            nargs_pattern = '(-*%s-*)' % '-*'.join('A' * nargs)

        # if this is an optional action, -- is not allowed
        if self.option_strings:
            nargs_pattern = nargs_pattern.replace('-*', '')
            nargs_pattern = nargs_pattern.replace('-', '')

        # return the pattern
        return nargs_pattern

    def _format_args(self, default_metavar):
        # moved from HelpFormatter
        # translate nargs into usage string
        get_metavar = self._metavar_formatter(default_metavar)
        if self.nargs is None:
            result = '%s' % get_metavar(1)
        elif self.nargs == OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif self.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % get_metavar(2)
        elif self.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % get_metavar(2)
        elif self.nargs == REMAINDER:
            result = '...'
        elif self.nargs == PARSER:
            result = '%s ...' % get_metavar(1)
        elif _is_mnrep(self.nargs):
            result = '%s%s' % (get_metavar(1)[0], self.nargs)
        elif self.nargs == SUPPRESS:
            result = ''

        else:
            if not isinstance(self.nargs, int):
                valid_nargs = [None,OPTIONAL,ZERO_OR_MORE,ONE_OR_MORE,REMAINDER,PARSER]
                msg = _('nargs %r not integer or %s'%(self.nargs, valid_nargs))
                raise ValueError(msg)
            formats = ['%s' for _ in range(self.nargs)]
            result = ' '.join(formats) % get_metavar(self.nargs)
        return result

    def _metavar_formatter(self, default_metavar):
        # return a function that returns a string or tuple
        if self.metavar is not None:
            result = self.metavar
        elif self.choices is not None:
            result = _format_choices(self.choices)
        else:
            result = default_metavar

        def format(tuple_size=None):
            if tuple_size is None:
                if isinstance(result, tuple):
                    # use get_name to convert tuple to string
                    return self.get_name(result)
                else:
                    return result
            else:
                if isinstance(result, tuple):
                    if len(result)==tuple_size:
                        return result
                    else:
                        msg = _('length of metavar tuple does not match nargs')
                        raise ValueError(msg)
                else:
                    return (result, ) * tuple_size

        return format

    def _format_tuple_metavar(self, formatter=None):
        # issue14074 - for positional, turn a tuple metavar into a
        # string that can be used for both help and error messages
        # some alternative versions
        return '|'.join(self.metavar)  # e.g W1|W2  W1..W2
        #return str(self.metavar)  # e.g.  ('W1', 'W2')
        #return self.metavar[0]   # e.g. W1
        #return self._format_args(self.dest) # e.g. W1 [W2 ...]

    def _is_nargs_variable(self):
        # return true if action takes variable number of args
        if self.nargs in [OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, REMAINDER, PARSER]:
            return True
        if _is_mnrep(self.nargs):
            return True
        return False

    def _check_value(self, value):
        # issue16468 version
        # converted value must be one of the choices (if specified)
        if self.choices is not None:
            choices = self.choices
            if isinstance(choices, str):
                # so 'in' does not find substrings
                choices = list(choices)
            try:
                aproblem = value not in choices
            except Exception as e:
                msg = _('invalid choice: %r, %s'%(value, e))
                # e.g. None not in 'astring'
                raise ArgumentError(self, msg)
            if aproblem:
                # summarize is # choices exceeds this value
                # is there a reasonable way of giving user control of this?
                args = {'value': value,
                        'choices': _format_choices(choices, summarize=15),
                        }
                msg = _('invalid choice: %(value)r (choose from %(choices)s)')
                raise ArgumentError(self, msg % args)

    def _check_values(self, values):
        # issue16468 version
        # converted value[s] must be one of the choices (if specified)
        if self.choices is None:
            return

        choices = self.choices
        if isinstance(choices, str):
            # so 'in' does not find substrings
            choices = list(choices)
        if not isinstance(values,(tuple, list)):
            values = (values,)
        try:
            problems = [value for value in values if value not in choices]
        except Exception as e:
            msg = _('invalid choice: %r, %s'%(value, e))
            # e.g. None not in 'astring'
            raise ArgumentError(self, msg)
        if problems:
            # summarize is # choices exceeds this value
            # is there a reasonable way of giving user control of this?
            #value = problems[0] # for now, just display 1st
            args = {'value': ','.join([str(p) for p in problems]),
                    'plural': 's' if len(problems)>1 else '',
                    'choices': _format_choices(choices, summarize=15),
                    }
            msg = _('invalid choice%(plural)s: %(value)r (choose from %(choices)s)')
            raise ArgumentError(self, msg % args)


    def _check_nargs(self):
       # check nargs and metavar tuple

        # test for {m,n} rep; convert a (m,n) tuple if needed
        try:
            nargs = _is_mnrep(self.nargs)
            if nargs:
                self.nargs = nargs
        except ValueError as e:
            raise ArgumentError(self, str(e))

        try:
            self._format_args(None)
        except (ValueError, AttributeError) as e:
            raise ArgumentError(self, str(e))

class _StoreAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for store actions must be > 0; if you '
                             'have nothing to store, actions such as store '
                             'true or store const may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class _StoreConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)


class _StoreTrueAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):
        super(_StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            required=required,
            help=help)


class _StoreFalseAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=True,
                 required=False,
                 help=None):
        super(_StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help)


class _AppendAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for append actions must be > 0; if arg '
                             'strings are not supplying the value to append, '
                             'the append const action may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)


class _AppendConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(self.const)
        setattr(namespace, self.dest, items)


class _CountAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 required=False,
                 help=None):
        super(_CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = _ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class _HelpAction(Action):

    def __init__(self,
                 option_strings,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()


class _VersionAction(Action):

    def __init__(self,
                 option_strings,
                 version=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help="show program's version number and exit"):
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser.exit(message=formatter.format_help())


class _SubParsersAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, aliases, help):
            metavar = dest = name
            if aliases:
                metavar += ' (%s)' % ', '.join(aliases)
            sup = super(_SubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=dest, help=help,
                         metavar=metavar)

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest=SUPPRESS,
                 required=True,
                 help=None,
                 metavar=None):

        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = _collections.OrderedDict()
        self._choices_actions = []

        super(_SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=PARSER,
            choices=self._name_parser_map,
            required=required,
            help=help,
            metavar=metavar)

    def add_parser(self, name, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        aliases = kwargs.pop('aliases', ())

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, aliases, help)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser

        # make parser available under aliases also
        for alias in aliases:
            self._name_parser_map[alias] = parser

        return parser

    def _get_subactions(self):
        return self._choices_actions

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            args = {'parser_name': parser_name,
                    'choices': ', '.join(self._name_parser_map)}
            msg = _('unknown parser %(parser_name)r (choices: %(choices)s)') % args
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them
        namespace, arg_strings = parser.parse_known_args(arg_strings, namespace)
        if arg_strings:
            vars(namespace).setdefault(_UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, _UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)

    def name(self):
        # custom name for get_name()
        return "{%s}"%','.join(self._name_parser_map)

# ==============
# Type classes
# ==============

class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
        - encoding -- The file's encoding. Accepts the same values as the
            builtin open() function.
        - errors -- A string indicating how encoding and decoding errors are to
            be handled. Accepts the same value as the builtin open() function.
    """

    def __init__(self, mode='r', bufsize=-1, encoding=None, errors=None):
        self._mode = mode
        self._bufsize = bufsize
        self._encoding = encoding
        self._errors = errors

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return _sys.stdin
            elif 'w' in self._mode:
                return _sys.stdout
            else:
                msg = _('argument "-" with mode %r') % self._mode
                raise ValueError(msg)

        # all other arguments are used as file names
        try:
            return open(string, self._mode, self._bufsize, self._encoding,
                        self._errors)
        except OSError as e:
            message = _("can't open '%s': %s")
            raise ArgumentTypeError(message % (string, e))

    def __repr__(self):
        args = self._mode, self._bufsize
        kwargs = [('encoding', self._encoding), ('errors', self._errors)]
        args_str = ', '.join([repr(arg) for arg in args if arg != -1] +
                             ['%s=%r' % (kw, arg) for kw, arg in kwargs
                              if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)

# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)

    def __contains__(self, key):
        return key in self.__dict__ or key.replace('-', '_') in self.__dict__

    def __getattr__(self, name):
        # Compatibility for people doing getattr(args, 'foo-bar') instead of
        # args.foo_bar. This might lead to some false positives, but this
        # is unlikely.
        try:
            return self.__dict__[name.replace('-', '_')]
        except KeyError:
            msg = _("'%s' object has no attribute '%s'")
            raise AttributeError(msg % (type(self).__name__, name))


class _ActionsContainer(object):

    def __init__(self,
                 description,
                 prefix_chars,
                 argument_default,
                 conflict_handler):
        super(_ActionsContainer, self).__init__()

        self.description = description
        self.argument_default = argument_default
        self.prefix_chars = prefix_chars
        self.conflict_handler = conflict_handler

        # set up registries
        self._registries = {}

        # register actions
        self.register('action', None, _StoreAction)
        self.register('action', 'store', _StoreAction)
        self.register('action', 'store_const', _StoreConstAction)
        self.register('action', 'store_true', _StoreTrueAction)
        self.register('action', 'store_false', _StoreFalseAction)
        self.register('action', 'append', _AppendAction)
        self.register('action', 'append_const', _AppendConstAction)
        self.register('action', 'count', _CountAction)
        self.register('action', 'help', _HelpAction)
        self.register('action', 'version', _VersionAction)
        self.register('action', 'parsers', _SubParsersAction)

        # raise an exception if the conflict handler is invalid
        self._get_handler()

        # action storage
        self._actions = []
        self._option_string_actions = {}

        # groups
        self._action_groups = []
        self._mutually_exclusive_groups = []

        # defaults storage
        self._defaults = {}

        # determines whether an "option" looks like a negative number
        self._negative_number_matcher = _re.compile(r'^-\d+$|^-\d*\.\d+$')

        # whether or not there are any optionals that look like negative
        # numbers -- uses a list so it can be shared and edited
        self._has_negative_number_optionals = []

    # ====================
    # Registration methods
    # ====================
    def register(self, registry_name, value, object):
        registry = self._registries.setdefault(registry_name, {})
        registry[value] = object

    def _registry_get(self, registry_name, value, default=None):
        return self._registries[registry_name].get(value, default)

    # ==================================
    # Namespace default accessor methods
    # ==================================
    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

        # if these defaults match any existing arguments, replace
        # the previous default on the object with the new one
        for action in self._actions:
            if action.dest in kwargs:
                action.default = kwargs[action.dest]

    def get_default(self, dest):
        for action in self._actions:
            if action.dest == dest and action.default is not None:
                return action.default
        return self._defaults.get(dest, None)


    # =======================
    # Adding argument actions
    # =======================
    def add_argument(self, *args, **kwargs):
        """
        add_argument(dest, ..., name=value, ...)
        add_argument(option_string, option_string, ..., name=value, ...)
        """

        # if no positional args are supplied or only one is supplied and
        # it doesn't look like an option string, parse a positional
        # argument
        chars = self.prefix_chars
        if not args or len(args) == 1 and args[0][0] not in chars:
            if args and 'dest' in kwargs:
                raise ValueError('dest supplied twice for positional argument')
            kwargs = self._get_positional_kwargs(*args, **kwargs)

        # otherwise, we're adding an optional argument
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)

        # if no default was supplied, use the parser-level default
        if 'default' not in kwargs:
            dest = kwargs['dest']
            if dest in self._defaults:
                kwargs['default'] = self._defaults[dest]
            elif self.argument_default is not None:
                kwargs['default'] = self.argument_default

        # create the action object, and add it to the parser
        action_class = self._pop_action_class(kwargs)
        if not callable(action_class):
            raise ValueError('unknown action "%s"' % (action_class,))
        action = action_class(**kwargs)

        # raise an error if the action type is not callable
        type_func = self._registry_get('type', action.type, action.type)
        if not callable(type_func):
            raise ValueError('%r is not callable' % (type_func,))

        action._check_nargs()
        return self._add_action(action)

    def add_argument_group(self, *args, **kwargs):
        group = _ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_mutually_exclusive_group(self, **kwargs):
        # works with and without a title
        if 'title' in kwargs:
            args = kwargs.copy()
            args.pop('required', None)
            container = self.add_argument_group(**args)
        else:
            container = self
        kwargs.pop('title', None)
        kwargs.pop('description', None)
        group = _MutuallyExclusiveGroup(container, **kwargs)
        #if hasattr(container, 'parser'):
        #    container.parser._mutually_exclusive_groups.append(group)
        container._mutually_exclusive_groups.append(group)

        return group

    def add_mutually_exclusive_group(self, **kwargs):
        # test replacing MXG with Nesting
        # all test_argparse works with this replacement
        if 'title' in kwargs:
            args = kwargs.copy()
            args.pop('required', None)
            container = self.add_argument_group(**args)
        else:
            container = self
        kwargs.pop('title', None)
        kwargs.pop('description', None)
        group = _NestingGroup(container, kind='mxg', **kwargs)
        container._mutually_exclusive_groups.append(group)
        return group

    def add_nested_group(self, *args, **kwargs):
        group = _NestingGroup(self, *args, **kwargs)
        #self._action_groups.append(group)
        if group.fn is None:
            # or test is self is not _NestingGroup
            # should a nestingGroup have such a list?
            self._mutually_exclusive_groups.append(group)
        return group

    def _add_action(self, action):
        # resolve any conflicts
        self._check_conflict(action)

        # add to actions list
        self._actions.append(action)
        action.container = self

        # index the action by any option strings it has
        for option_string in action.option_strings:
            self._option_string_actions[option_string] = action

        # set the flag if any option strings look like negative numbers
        for option_string in action.option_strings:
            if self._negative_number_matcher.match(option_string):
                if not self._has_negative_number_optionals:
                    self._has_negative_number_optionals.append(True)

        # return the created action
        return action

    def _remove_action(self, action):
        self._actions.remove(action)

    def _add_container_actions(self, container):
        # use to load data from parents
        # collect groups by titles
        title_group_map = {}
        for group in self._action_groups:
            if group.title in title_group_map:
                msg = _('cannot merge actions - two groups are named %r')
                raise ValueError(msg % (group.title))
            title_group_map[group.title] = group

        # map each action to its group
        group_map = {}
        for group in container._action_groups:

            # if a group with the title exists, use that, otherwise
            # create a new group matching the container's group
            if group.title not in title_group_map:
                title_group_map[group.title] = self.add_argument_group(
                    title=group.title,
                    description=group.description,
                    conflict_handler=group.conflict_handler)

            # map the actions to their new group
            for action in group._group_actions:
                group_map[action] = title_group_map[group.title]

        # add container's mutually exclusive groups
        # NOTE: if add_mutually_exclusive_group ever gains title= and
        # description= then this code will need to be expanded as above
        for group in container._mutually_exclusive_groups:
            mutex_group = self.add_mutually_exclusive_group(
                required=group.required)

            # map the actions to their new mutex group
            for action in group._group_actions:
                group_map[action] = mutex_group

        # add all actions to this container or their group
        for action in container._actions:
            group_map.get(action, self)._add_action(action)

    def _get_positional_kwargs(self, dest, **kwargs):
        # make sure required is not specified
        if 'required' in kwargs:
            msg = _("'required' is an invalid argument for positionals")
            raise TypeError(msg)

        # mark positional arguments as required if at least one is
        # always required
        if kwargs.get('nargs') not in [OPTIONAL, ZERO_OR_MORE]:
            kwargs['required'] = True
        #if kwargs.get('nargs') == ZERO_OR_MORE and 'default' not in kwargs:
        #    kwargs['required'] = True
        # this change is required if seen_non_deault_actions is
        # used for the required actions test.

        # make dest attribute-accessible, 'foo-bar' -> 'foo_bar'
        dest = dest.replace('-', '_')

        # return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = []
        long_option_strings = []
        for option_string in args:
            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                args = {'option': option_string,
                        'prefix_chars': self.prefix_chars}
                msg = _('invalid option string %(option)r: '
                        'must start with a character %(prefix_chars)r')
                raise ValueError(msg % args)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
                if len(option_string) > 1:
                    if option_string[1] in self.prefix_chars:
                        long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest_option_string = long_option_strings[0]
            else:
                dest_option_string = option_strings[0]
            dest = dest_option_string.lstrip(self.prefix_chars)
            if not dest:
                msg = _('dest= is required for options like %r')
                raise ValueError(msg % option_string)
            dest = dest.replace('-', '_')

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def _pop_action_class(self, kwargs, default=None):
        action = kwargs.pop('action', default)
        return self._registry_get('action', action, action)

    def _get_handler(self):
        # determine function from conflict handler string
        handler_func_name = '_handle_conflict_%s' % self.conflict_handler
        try:
            return getattr(self, handler_func_name)
        except AttributeError:
            msg = _('invalid conflict_resolution value: %r')
            raise ValueError(msg % self.conflict_handler)

    def _check_conflict(self, action):

        # find all options that conflict with this option
        confl_optionals = []
        for option_string in action.option_strings:
            if option_string in self._option_string_actions:
                confl_optional = self._option_string_actions[option_string]
                confl_optionals.append((option_string, confl_optional))

        # resolve any conflicts
        if confl_optionals:
            conflict_handler = self._get_handler()
            conflict_handler(action, confl_optionals)

    def _handle_conflict_error(self, action, conflicting_actions):
        message = ngettext('conflicting option string: %s',
                           'conflicting option strings: %s',
                           len(conflicting_actions))
        conflict_string = ', '.join([option_string
                                     for option_string, action
                                     in conflicting_actions])
        raise ArgumentError(action, message % conflict_string)

    def _handle_conflict_resolve(self, action, conflicting_actions):

        # remove all conflicting options
        for option_string, action in conflicting_actions:

            # remove the conflicting option
            action.option_strings.remove(option_string)
            self._option_string_actions.pop(option_string, None)

            # if the option now has no option string, remove it from the
            # container holding it
            if not action.option_strings:
                action.container._remove_action(action)


class _ArgumentGroup(_ActionsContainer):

    def __init__(self, container, title=None, description=None, **kwargs):
        # add any missing keyword arguments by checking the container
        update = kwargs.setdefault
        update('conflict_handler', container.conflict_handler)
        update('prefix_chars', container.prefix_chars)
        update('argument_default', container.argument_default)
        super_init = super(_ArgumentGroup, self).__init__
        super_init(description=description, **kwargs)

        # group attributes
        self.title = title
        self._group_actions = []

        # share most attributes with the container
        self._registries = container._registries
        self._actions = container._actions
        self._option_string_actions = container._option_string_actions
        self._defaults = container._defaults
        self._has_negative_number_optionals = \
            container._has_negative_number_optionals
        self._mutually_exclusive_groups = container._mutually_exclusive_groups

    def _add_action(self, action):
        action = super(_ArgumentGroup, self)._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        super(_ArgumentGroup, self)._remove_action(action)
        self._group_actions.remove(action)

    """
    as a container a group has _action_groups and _mutually_exclusive_groups
    why should container share m_e_g?
    add_m_e_g appends the group to the shared list
        that way the parser sees the m_e_g
        the group (if different) doesnt need to know about it
    _add_container_actions is only used to add a parent
        that's a complex bit of code

    remove_action used test_argparse.TestConflictHandling

    an m_e_g records its container, an a_g does not

    a parser makes use of its _mutually_exclusive_groups (for setting up test and usage)
    but a group has no use for it
    """

class _MutuallyExclusiveGroup(_ArgumentGroup):

    def __init__(self, container, required=False):
        super(_MutuallyExclusiveGroup, self).__init__(container)
        self.required = required
        self._container = container
        # register the test for this type of group
        # self.register works since parser and groups share _registers
        if self._registry_get('cross_tests','mxg', None) is None:
            # this test isn't essential, but in more general case we shouldn't
            # register the same test multiple times
            mytest = _MutuallyExclusiveGroup.test_mut_ex_groups
            self.register('cross_tests', 'mxg', mytest)
        name = str(id(self)) # a unique key for this test
        self.register('cross_tests', name, self.test_this_group)

    def _add_action(self, action):
        if action.required:
            msg = _('mutually exclusive arguments must be optional')
            raise ValueError(msg)
        action = self._container._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        self._container._remove_action(action)
        self._group_actions.remove(action)

    def add_argument(self, *args, **kwargs):
        # add extension that allows adding a prexisting Action
        # alt for issue10984 multigroup
        if len(args) and isinstance(args[0], Action):
            # add the action to self, but not to the parser (already there)
            action =  args[0]
            return self._group_actions.append(action)
        else:
            return super(_MutuallyExclusiveGroup, self).add_argument(*args, **kwargs)

    @staticmethod
    def test_mut_ex_groups(parser, seen_non_default_actions, *vargs, **kwargs):
        # alternative mutually_exclusive_groups test
        # performed once at end of parse_args rather than with each entry
        # the arguments listed in the error message may differ
        # this gives a small speed improvement
        # more importantly it is easier to customize and expand
        # from argdev/inclusive

        seen_actions = set(seen_non_default_actions)

        for group in parser._mutually_exclusive_groups:
            group_actions = group._group_actions
            group_seen = seen_actions.intersection(group_actions)
            cnt = len(group_seen)
            if cnt > 1:
                msg = 'only one the arguments %s is allowed'
            elif cnt == 0 and group.required:
                msg = 'one of the arguments %s is required'
            else:
                msg = None
            if msg:
                names = [_get_action_name(action)
                            for action in group_actions
                            if action.help is not SUPPRESS]
                parser.error(msg % ' '.join(names))
        print('testing mxg groups')

    def test_this_group(self, parser, seen_non_default_actions, *vargs, **kwargs):
        # test to be run near end of parsing
        seen_actions = set(seen_non_default_actions)

        group_actions = self._group_actions
        group_seen = seen_actions.intersection(group_actions)
        cnt = len(group_seen)
        if cnt > 1:
            msg = 'only one the arguments %s is allowed'
        elif cnt == 0 and self.required:
            msg = 'one of the arguments %s is required'
        else:
            msg = None
        if msg:
            names = [_get_action_name(action)
                        for action in group_actions
                        if action.help is not SUPPRESS]
            parser.error(msg % ' '.join(names))
        print('mxg testing',[a.dest for a in group_actions])

class _NestingGroup(_ArgumentGroup):

    def __init__(self, container, **kwargs):
        kind = kwargs.pop('kind', None)
        dest = kwargs.pop('dest', '')
        required = kwargs.pop('required', False)
        super(_NestingGroup, self).__init__(container, **kwargs)
        self.container = container  # _container to be consistent with MXG
        self.dest = dest
        self.required = required
        if isinstance(container, ArgumentParser):
            self.parser = container
        else:
            self.parser = getattr(container, 'parser', container)
        self.kind = kind
        name = str(id(self)) # a unique key for this test
        # print(name,self.dest, self.kind)
        if self.kind in ['mxg']:
            fn = self.test_mx_group # mutually exclusive
            joiner = ' | ' # something better for xor?
        elif self.kind in ['inc']:
            fn = self.test_inc_group # inclusive
            joiner = ' & '
        elif self.kind in ['any']:
            fn = self.test_any_group # any
            joiner =' | '
        else:
            fn = self.test_this_group
            joiner = ' , '
        self.joiner = joiner
        if isinstance(self.container, _NestingGroup):
            # save fn on self
            self.fn = fn
        else: # register fn with common register (container)
            self.fn = None
            self.container.register('cross_tests', name, fn)
        # attributes to help format this group
        # make it look like an action
        self.help = 'nested group help'
        self.option_strings = ''

    def _format_args(self, *args):
        return ''

    def _add_action(self, action):
        if self.kind in ['mxg'] and action.required:
            msg = _('mutually exclusive arguments must be optional')
            raise ValueError(msg)
        # add action to parser, but not container
        action = self.parser._add_action(action)
        self._group_actions.append(action)
        return action

    def add_nested_group(self, *args, **kwargs):
        # if this is nested group, add the new group to its own _group_actions
        group = super(_NestingGroup, self).add_nested_group(*args, **kwargs)
        self._group_actions.append(group)
        return group

    def add_argument(self, *args, **kwargs):
        # add extension that allows adding a prexisting Action
        if len(args) and isinstance(args[0], Action):
            # add the action to self, but not to the parser (already there)
            action =  args[0]
            return self._group_actions.append(action)
        else:
            return super(_NestingGroup, self).add_argument(*args, **kwargs)

    def test_this_group(self, parser, seen_non_default_actions, *vargs, **kwargs):
        # test to be run near end of parsing
        seen_actions = set(seen_non_default_actions)

        group_actions = self._group_actions
        group_seen = seen_actions.intersection(group_actions)
        cnt = len(group_seen)
        print('nested testing',[a.dest for a in group_actions])

    def count_actions(self, parser, seen_actions, *vargs, **kwargs):
        # utility that is useful in most kinds of tests
        # count the number of actions that were seen
        # handles nested groups
        seen_actions = set(seen_actions)
        group_actions = self._group_actions
        actions = [a for a in group_actions if isinstance(a, Action)]
        groups = [a for a in group_actions if isinstance(a, _NestingGroup)]
        okgroups = [a for a in groups if a.fn(parser, seen_actions, *vargs, **kwargs)]
        okgroups = set(okgroups)
        # print('ok group', [g.dest for g in okgroups])
        # if a group tests as ok (no error) it counts as 'seen'
        group_seen = seen_actions.intersection(actions)
        group_seen = group_seen.union(okgroups)
        cnt = len(group_seen)
        return cnt

    def test_mx_group(self, parser, seen_non_default_actions, *vargs, **kwargs):
        # test equivalent the mutually_exclusive_groups
        seen_actions = set(seen_non_default_actions)

        group_actions = self._group_actions
        cnt = self.count_actions(parser, seen_non_default_actions, *vargs, **kwargs)
        if cnt > 1:
            msg = '%s: only one the arguments [%s] is allowed'
        elif cnt == 0 and self.required:
            msg = '%s: one of the arguments [%s] is required'
        else:
            msg = None
        if msg:
            names = ' '.join([action.dest for action in group_actions])
            parser.error(msg % (self.dest, names))
        return cnt>0 # True if something present, False if none

    def test_inc_group(self, parser, seen_non_default_actions, *vargs, **kwargs):
        # inclusive group - if one is present, all must be present
        # if group is required, all are required
        group_actions = self._group_actions
        cnt = self.count_actions(parser, seen_non_default_actions, *vargs, **kwargs)
        if cnt > 0: # if any
            if cnt < len(group_actions): # all
                msg = '%s: all of the arguments [%s] are required'
            else:
                msg = None
        elif cnt == 0 and self.required:
            msg = '%s: all of the arguments [%s] is required'
        else:
            msg = None
        if msg:
            names = ' '.join([action.dest for action in group_actions])
            parser.error(msg % (self.dest, names))
        print('inc testing',[a.dest for a in group_actions])
        return cnt>0

    def test_any_group(self, parser, seen_non_default_actions, *vargs, **kwargs):
        # any may be present (or atleast one if group is required)
        group_actions = self._group_actions
        cnt = self.count_actions(parser, seen_non_default_actions, *vargs, **kwargs)
        if cnt == 0 and self.required:
            msg = 'some of the arguments %s is required'
        else:
            msg = None
        if msg:
            names = [action.dest for action in group_actions]
            parser.error(msg % ' '.join(names))
        print('any testing',[a.dest for a in group_actions])
        return cnt>0

    # group_actions can include actions and other _NestingGroups
    # 'kind' denotes some sort of test, e.g. like mut-exclusive
    #    mut-exclusive - like m-e-g but allows for 'presense' of ngroup
    #       ie at most one of actions or groups allowed
    #       x req = only one allowed
    #    mut-inclusive - all present
    #    mut-any - cnt >=0, or >0 if required
    #    mut-null - no test

    # add some sort of usage formatting; symbol atleast (| for mxg; & for inc)
    # diff between true or, and xor; maybe symbol is a string
    # group does not have attribute 'get_name', nor 'help'

class ArgumentParser(_AttributeHolder, _ActionsContainer):
    """Object for parsing command line strings into Python objects.

    Keyword Arguments:
        - prog -- The name of the program (default: sys.argv[0])
        - usage -- A usage message (default: auto-generated from arguments)
        - description -- A description of what the program does
        - epilog -- Text following the argument descriptions
        - parents -- Parsers whose arguments should be copied into this one
        - formatter_class -- HelpFormatter class for printing help messages
        - prefix_chars -- Characters that prefix optional arguments
        - fromfile_prefix_chars -- Characters that prefix files containing
            additional arguments
        - argument_default -- The default value for all arguments
        - conflict_handler -- String indicating how to handle conflicts
        - add_help -- Add a -h/-help option
    """

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 parents=[],
                 formatter_class=HelpFormatter,
                 prefix_chars='-',
                 fromfile_prefix_chars=None,
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True,
                 args_default_to_positional=False,
                 ):

        superinit = super(ArgumentParser, self).__init__
        superinit(description=description,
                  prefix_chars=prefix_chars,
                  argument_default=argument_default,
                  conflict_handler=conflict_handler)

        # default setting for prog
        if prog is None:
            prog = _os.path.basename(_sys.argv[0])

        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.formatter_class = formatter_class
        self.fromfile_prefix_chars = fromfile_prefix_chars
        self.add_help = add_help
        self.args_default_to_positional = args_default_to_positional

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('optional arguments'))
        self._subparsers = None

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)

        # initialize cross_tests
        # self.register('cross_tests', ?,?)
        self._registries['cross_tests'] = {}

        # add help argument if necessary
        # (using explicit default to override global argument_default)
        default_prefix = '-' if '-' in prefix_chars else prefix_chars[0]
        if self.add_help:
            self.add_argument(
                default_prefix+'h', default_prefix*2+'help',
                action='help', default=SUPPRESS,
                help=_('show this help message and exit'))

        # add parent arguments and defaults
        for parent in parents:
            self._add_container_actions(parent)
            try:
                defaults = parent._defaults
            except AttributeError:
                pass
            else:
                self._defaults.update(defaults)

    # =======================
    # Pretty __repr__ methods
    # =======================
    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]

    # ==================================
    # Optional/Positional adding methods
    # ==================================
    def add_subparsers(self, **kwargs):
        if self._subparsers is not None:
            self.error(_('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        if 'title' in kwargs or 'description' in kwargs:
            title = _(kwargs.pop('title', 'subcommands'))
            description = _(kwargs.pop('description', None))
            self._subparsers = self.add_argument_group(title, description)
        else:
            self._subparsers = self._positionals

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            positionals = self._get_positional_actions()
            groups = self._mutually_exclusive_groups
            formatter.add_usage(self.usage, positionals, groups, '')
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._subparsers._add_action(action)

        # return the created parsers action
        return action

    def _add_action(self, action):
        if action.option_strings:
            self._optionals._add_action(action)
        else:
            self._positionals._add_action(action)
        return action

    def _get_optional_actions(self):
        return [action
                for action in self._actions
                if action.option_strings]

    def _get_positional_actions(self):
        return [action
                for action in self._actions
                if not action.option_strings]

    # =====================================
    # Command line argument parsing methods
    # =====================================
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s')
            self.error(msg % ' '.join(argv))
        return args

    def parse_known_args(self, args=None, namespace=None):
        if args is None:
            # args default to the system args
            args = _sys.argv[1:]
        else:
            # make sure that args are mutable
            args = list(args)

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, str):
                            default = _DelayedValue(self._get_value, action, default)
                            default.__name__ = 'delayed_get_value'
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            namespace, args = self._parse_known_args(args, namespace)

            # evaluate any _DelayedValues left in the namespace
            # was in _parse_known_args
            for action in self._actions:
                value = getattr(namespace, action.dest, None)
                if isinstance(value, _DelayedValue):
                    assert value.func.__name__=='_get_value'
                    setattr(namespace, action.dest, value())


            if hasattr(namespace, _UNRECOGNIZED_ARGS_ATTR):
                args.extend(getattr(namespace, _UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, _UNRECOGNIZED_ARGS_ATTR)
            return namespace, args
        except ArgumentError:
            err = _sys.exc_info()[1]
            self.error(str(err))

    def _parse_known_args(self, arg_strings, namespace):
        # replace arg strings that are file references
        if self.fromfile_prefix_chars is not None:
            arg_strings = self._read_args_from_files(arg_strings)

        """
        # map all mutually exclusive arguments to the other arguments
        # they can't occur with
        action_conflicts = {}
        for mutex_group in self._mutually_exclusive_groups:
            group_actions = mutex_group._group_actions
            for i, mutex_action in enumerate(mutex_group._group_actions):
                conflicts = action_conflicts.setdefault(mutex_action, [])
                conflicts.extend(group_actions[:i])
                conflicts.extend(group_actions[i + 1:])
        """

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuple = self._parse_optional(arg_string)
                if option_tuple is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuple
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        seen_actions = set()
        seen_non_default_actions = [] # set()

        def take_action(action, argument_strings, option_string=None):
            seen_actions.add(action)
            argument_values, using_default = self._get_values(action, argument_strings)

            # error if this argument is not allowed with other previously
            # seen arguments, assuming that actions that use the default
            # value don't really count as "present"
            # refine test so that only values set by _get_values() to
            # action.default count as not-really-present

            if not using_default:
                seen_non_default_actions.append(action) #add(action)
                """
                for conflict_action in action_conflicts.get(action, []):
                    if conflict_action in seen_non_default_actions:
                        msg = _('not allowed with argument %s')
                        action_name = conflict_action.get_name()
                        raise ArgumentError(action, msg % action_name)
                """

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not SUPPRESS:
                action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index, no_action=False, penult=-1):

            # get the optional identified at this index
            option_tuple = option_string_indices[start_index]
            action, option_string, explicit_arg = option_tuple

            # identify additional optionals in the same arg string
            # (e.g. -xyz is the same as -x -y -z if no args are required)
            match_argument = self._match_argument
            action_tuples = []
            while True:

                # if we found no optional action, skip it
                if action is None:
                    extras.append(arg_strings[start_index])
                    return start_index + 1

                # if there is an explicit argument, try to match the
                # optional's string arguments to only this
                if explicit_arg is not None:
                    arg_count = match_argument(action, 'A')

                    # if the action is a single-dash option and takes no
                    # arguments, try to parse more single-dash options out
                    # of the tail of the option string
                    chars = self.prefix_chars
                    if arg_count == 0 and option_string[1] not in chars:
                        action_tuples.append((action, [], option_string))
                        char = option_string[0]
                        option_string = char + explicit_arg[0]
                        new_explicit_arg = explicit_arg[1:] or None
                        optionals_map = self._option_string_actions
                        if option_string in optionals_map:
                            action = optionals_map[option_string]
                            explicit_arg = new_explicit_arg
                        else:
                            msg = _('ignored explicit argument %r')
                            raise ArgumentError(action, msg % explicit_arg)

                    # if the action expect exactly one argument, we've
                    # successfully matched the option; exit the loop
                    elif arg_count == 1:
                        stop = start_index + 1
                        args = [explicit_arg]
                        action_tuples.append((action, args, option_string))
                        break

                    # error if a double-dash option did not use the
                    # explicit argument
                    else:
                        msg = _('ignored explicit argument %r')
                        raise ArgumentError(action, msg % explicit_arg)

                # if there is no explicit argument, try to match the
                # optional's string arguments with the following strings
                # if successful, exit the loop
                else:
                    start = start_index + 1
                    selected_patterns = arg_strings_pattern[start:]
                    arg_count = match_argument(action, selected_patterns)

                    # if action takes a variable number of arguments, see
                    # if it needs to share any with remaining positionals
                    if action._is_nargs_variable():
                        # variable range of args for this action
                        slots = self._match_arguments_partial([action]+positionals, selected_patterns)
                        shared_count = slots[0]
                    else:
                        shared_count = None

                    # penult controls whether this uses this shared_count
                    # the last optional (ultimate) usually can share
                    # but earlier ones (penult) might also

                    if shared_count is not None and selected_patterns.count('O')<=penult:
                        if arg_count>shared_count:
                            arg_count = shared_count

                    stop = start + arg_count
                    args = arg_strings[start:stop]
                    action_tuples.append((action, args, option_string))
                    break

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            if no_action:
                return stop
            assert action_tuples
            for action, args, option_string in action_tuples:
                take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = self._get_positional_actions()

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index, no_action=False):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # if we haven't hit the end of the command line strings,
            # then don't consume any final zero-width arguments yet
            # (we may need to parse some more optionals first)
            # if start_index + sum(arg_counts) != len(arg_strings_pattern):
            if 'O' in selected_pattern: # better 15112 test
                while arg_counts and arg_counts[-1] == 0:
                    arg_counts.pop()

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]

                if action.nargs not in [PARSER, REMAINDER]: # issue 13922
                    pats = arg_strings_pattern[start_index: start_index + arg_count]
                    # remove '--' corresponding to a '-' in pattern
                    try:
                        ii = pats.index('-')
                        assert(args[ii]=='--')
                        del args[ii]
                    except ValueError:
                        pass

                start_index += arg_count
                if not no_action:
                    take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        def consume_loop(no_action=False, penult=-1):

            # consume Positionals and Optionals alternately, until we have
            # passed the last option string

            start_index = 0
            if option_string_indices:
                max_option_string_index = max(option_string_indices)
            else:
                max_option_string_index = -1

            while start_index <= max_option_string_index:
                # consume any Positionals preceding the next option
                next_option_string_index = min([
                    index
                    for index in option_string_indices
                    if index >= start_index])
                if start_index != next_option_string_index:
                    positionals_end_index = consume_positionals(start_index,no_action)

                    # only try to parse the next optional if we didn't consume
                    # the option string during the positionals parsing
                    if positionals_end_index > start_index:
                        start_index = positionals_end_index
                        continue
                    else:
                        start_index = positionals_end_index

                # if we consumed all the positionals we could and we're not
                # at the index of an option string, there were extra arguments
                if start_index not in option_string_indices:
                    strings = arg_strings[start_index:next_option_string_index]
                    extras.extend(strings)
                    start_index = next_option_string_index

                # consume the next optional and any arguments for it
                start_index = consume_optional(start_index,no_action,penult)
            # consume any positionals following the last Optional
            stop_index = consume_positionals(start_index,no_action)

            # if we didn't consume all the argument strings, there were extras
            extras.extend(arg_strings[stop_index:])
            return extras

        penult = arg_strings_pattern.count('O') # # of 'O' in 'AOAA' patttern
        opt_actions = [v[0] for v in option_string_indices.values() if v[0]]

        _cnt = 0
        if self._is_nargs_variable(opt_actions) and positionals and penult>1:
            # if there are positionals and one or more 'variable' optionals
            # do test loops to see when to start sharing
            # test loops
            for ii in range(0, penult):
                extras = []
                positionals = self._get_positional_actions()
                extras = consume_loop(True, ii)
                _cnt += 1
                if len(positionals)==0:
                    break
        else:
            # don't need a test run; but do use action+positionals parsing
            ii = 0
        # now the real parsing loop, that takes action
        extras = []
        positionals = self._get_positional_actions()
        extras = consume_loop(False, ii)
        _cnt += 1

        # make sure all required actions were present
        required_actions = []
        for action in self._actions:
            if action not in seen_non_default_actions: # seen_actions:
                if action.required:
                    required_actions.append(action.get_name())
                """
                else:
                    # evaluate the value in the namespace if it is a
                    # wrapped _get_value function
                    value = getattr(namespace, action.dest, None)
                    if isinstance(value, _DelayedValue):
                        assert value.func.__name__=='_get_value'
                        setattr(namespace, action.dest, value())
                """

        if required_actions:
            required_actions = ['%s'%name for name in required_actions]
            self.error(_('the following arguments are required: %s') %
                       ', '.join(required_actions))

        """
        # make sure all required groups had one option present
        for group in self._mutually_exclusive_groups:
            if group.required:
                for action in group._group_actions:
                    if action in seen_non_default_actions:
                        break

                # if no actions were used, report the error
                else:
                    names = [action.get_name()
                             for action in group._group_actions
                             if action.help is not SUPPRESS]
                    names = ['%s'%name for name in names]
                    msg = _('one of the arguments %s is required')
                    self.error(msg % ' '.join(names))
        """
        # give user a hook to run more general tests on arguments
        # its primary purpose is to give the user access to seen_non_default_actions
        # I can't think of a case where seen_actions is better - so omit
        for testkey, testfn in self._get_cross_tests():
            testfn(self, seen_non_default_actions, seen_actions, namespace, extras, key=testkey)

        # return the updated namespace and the extra arguments
        return namespace, extras

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if not arg_string or arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    with open(arg_string[1:]) as args_file:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                except OSError:
                    err = _sys.exc_info()[1]
                    self.error(str(err))

        # return the modified argument list
        return new_arg_strings

    def convert_arg_line_to_args(self, arg_line):
        return [arg_line]

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = action._get_nargs_pattern()
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: _('expected one argument'),
                OPTIONAL: _('expected at most one argument'),
                ONE_OR_MORE: _('expected at least one argument'),
            }
            default = ngettext('expected %s argument',
                               'expected %s arguments',
                               action.nargs) % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        result = []
        for i in range(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join([action._get_nargs_pattern()
                               for action in actions_slice])
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend([len(string) for string in match.groups()])
                break

        # return the list of arg string counts
        return result

    def _get_nested_action(self, arg_string):
        # recursively seek arg_string in subparsers
        if self._subparsers is not None:
            for action in self._subparsers._actions:
                if isinstance(action, _SubParsersAction):
                    for parser in action._name_parser_map.values():
                        if arg_string in parser._option_string_actions:
                            return parser._option_string_actions[arg_string]
                        else:
                            sub_action = parser._get_nested_action(arg_string)
                            if sub_action is not None:
                                return sub_action
        return None

    def _parse_optional(self, arg_string):
        # if it's an empty string, it was meant to be a positional
        if not arg_string:
            return None

        # if it doesn't start with a prefix, it was meant to be positional
        if not arg_string[0] in self.prefix_chars:
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return action, arg_string, None

        if getattr(self, 'scan', True):
            # parser.scan temporary testing switch
            # if arg_string is found in a subparser, treat as an unknown
            # optional
            if self._get_nested_action(arg_string):
                return None, arg_string, None

        # if it's just a single character, it was meant to be positional
        if len(arg_string) == 1:
            return None

        # if the option string before the "=" is present, return the action
        if '=' in arg_string:
            option_string, explicit_arg = arg_string.split('=', 1)
            if option_string in self._option_string_actions:
                action = self._option_string_actions[option_string]
                return action, option_string, explicit_arg

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        # if multiple actions match, the option string was ambiguous
        if len(option_tuples) > 1:
            options = ', '.join([option_string
                for action, option_string, explicit_arg in option_tuples])
            args = {'option': arg_string, 'matches': options}
            msg = _('ambiguous option: %(option)s could match %(matches)s')
            self.error(msg % args)

        # if exactly one action matched, this segmentation is good,
        # so return the parsed action
        elif len(option_tuples) == 1:
            option_tuple, = option_tuples
            return option_tuple

        # behave more like optparse even if the argument looks like a option
        if self.args_default_to_positional:
            return None

        # if it is not found as an option, but looks like a number
        # it is meant to be positional
        # unless there are negative-number-like options
        # try complex() is more general than self._negative_number_matcher
        if not self._has_negative_number_optionals:
            try:
                complex(arg_string)
                return None
            except ValueError:
                pass

        # if it contains a space, it was meant to be a positional
        if ' ' in arg_string:
            return None

        # it was meant to be an optional but there is no such option
        # in this parser (though it might be a valid option in a subparser)
        return None, arg_string, None

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '='
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if '=' in option_string:
                option_prefix, explicit_arg = option_string.split('=', 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            self.error(_('unexpected option string: %s') % option_string)

        # return the collected option tuples
        return result

    #def _get_nargs_pattern(self, action):
    #    return action._get_nargs_pattern()

    def _is_nargs_variable(self, actions):
        # return true if  any action in a list, takes variable number of args
        return any(a._is_nargs_variable() for a in actions)

    def _get_cross_tests(self):
        # fetch a list (possibly empty) of tests to be run at the end of parsing
        # for example, the mutually_exclusive_group tests
        # or user supplied tests
        # issue11588

        # this could be in a 'parser.cross_tests' attribute
        # tests = getattr(self, 'cross_tests', [])
        # but here I am looking in the _registries
        # _registries is already shared among groups
        # allowing me to define the group tests in the group class itself
        # This use of _registries is slight non_standard since I am
        # ignoring the 2nd level keys
        tests = self._registries['cross_tests'].items() # values()
        return tests

    def crosstest(self, func):
        # decorator to facilitate adding these functions
        name = func.__name__
        self.register('cross_tests', name, func)

    # ========================
    # Value conversion methods
    # ========================

    def _get_values(self, action, arg_strings):
        # for everything but PARSER, REMAINDER args, strip out first '--'
        using_default = False
        # -- removed in comsume_positionals issue13922
        #if action.nargs not in [PARSER, REMAINDER]:
        #    try:
        #        arg_strings.remove('--')
        #    except ValueError:
        #        pass

        # optional argument produces a default when not present
        if not arg_strings and action.nargs == OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
                using_default = True
            if isinstance(value, str):
                value = self._get_value(action, value)
                action._check_values(value)

        # when nargs='*' on a positional, if there were no command-line
        # args, use the default if it is anything other than None
        elif (not arg_strings and action.nargs == ZERO_OR_MORE and
              not action.option_strings):
            if action.default is not None:
                value = action.default
            else:
                value = arg_strings # []
            using_default = True
            if isinstance(value, str):
                action._check_values(value)
            # minimal change from existing - check a string
            # do nothing special with other values (most likely a list)
            # see issue9625

        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            action._check_values(value)

        # REMAINDER arguments convert all values, checking none
        elif action.nargs == REMAINDER:
            value = [self._get_value(action, v) for v in arg_strings]

        # PARSER arguments convert all values, but check only the first
        elif action.nargs == PARSER:
            value = [self._get_value(action, v) for v in arg_strings]
            action._check_values(value[0])

        # all other types of nargs produce a list
        else:
            value = [self._get_value(action, v) for v in arg_strings]
            action._check_values(value)

        # return the converted value
        return value, using_default


    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except ArgumentTypeError:
            name = getattr(action.type, '__name__', repr(action.type))
            msg = str(_sys.exc_info()[1])
            raise ArgumentError(action, msg)

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            args = {'type': name, 'value': arg_string}
            msg = _('invalid %(type)s value: %(value)r')
            raise ArgumentError(action, msg % args)

        # return the converted value
        return result

    # =======================
    # Help-formatting methods
    # =======================
    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        return formatter.format_help()

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================
    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_help(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = _sys.stderr
            file.write(message)

    # ===============
    # Exiting methods
    # ===============
    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, _sys.stderr)
        _sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(_sys.stderr)
        args = {'prog': self.prog, 'message': message}
        self.exit(2, _('%(prog)s: error: %(message)s\n') % args)
