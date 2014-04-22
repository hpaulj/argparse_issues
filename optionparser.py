from argparse import ArgumentParser, Namespace, SUPPRESS, ArgumentError
import sys as _sys
from gettext import gettext as _, ngettext
from optparse import _match_abbrev, BadOptionError, OptionValueError

class OptionParser(ArgumentParser):
    """attempt to replicate the optparse parse_args
    """
    def parse_opts(self, args=None, namespace=None):
        """
        parse_args(args : [string] = sys.argv[1:],
                   values : Values = None)
        -> (values : Values, args : [string])

        Parse the command-line options found in 'args' (default:
        sys.argv[1:]).  Any errors result in a call to 'error()', which
        by default prints the usage message to stderr and calls
        sys.exit() with an error message.  On success returns a pair
        (values, args) where 'values' is an Values instance (with all
        your option values) and 'args' is the list of arguments left
        over after parsing options.
        """
        # test for attribute used by optparse but not argparse
        # can be set directly
        try:
            self.allow_interspersed_args
        except AttributeError:
            self.allow_interspersed_args = True

        rargs = self._get_args(args)
        namespace = self.get_default_values(namespace)

        # Store the halves of the argument list as attributes for the
        # convenience of callbacks:
        #   rargs
        #     the rest of the command-line (the "r" stands for
        #     "remaining" or "right-hand")
        #   largs
        #     the leftover arguments -- ie. what's left after removing
        #     options and their arguments (the "l" stands for "leftover"
        #     or "left-hand")
        self.rargs = rargs  # argstrings
        self.largs = largs = []
        self.namespace = namespace

        try:
            stop = self._process_args(largs, rargs)
        except ArgumentError:
            err = _sys.exc_info()[1]
            self.error(str(err))
        except (BadOptionError, OptionValueError) as err:
            self.error(str(err))

        args = largs + rargs
        return namespace, args # self.check_values(namespace, args)

    def _get_args(self, args):
        if args is None:
            return _sys.argv[1:]
        else:
            return args[:]              # don't modify caller's list

    def get_default_values(self, namespace):
        # default Namespace built from parser defaults
        # adapt from parse_known_args
        # python2.7 before the latest delayed evaluation change
        if namespace is None:
            namespace = Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, str):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        return namespace

    def _process_args(self, largs, rargs):
        """_process_args(largs : [string],
                         rargs : [string],
                         namespace : Values)

        Process command-line arguments and populate 'namespace', consuming
        options and arguments from 'rargs'.  If 'allow_interspersed_args' is
        false, stop at the first non-option argument.  If true, accumulate any
        interspersed non-option arguments in 'largs'.
        """
        while rargs:
            arg = rargs[0]
            # We handle bare "--" explicitly, and bare "-" is handled by the
            # standard arg handler since the short arg case ensures that the
            # len of the opt string is greater than 1.
            if arg == "--":
                del rargs[0]
                return
            elif arg[0:2] == "--":
                # process a single long option (possibly with value(s))
                self._process_long_opt(rargs)
            elif arg[:1] == "-" and len(arg) > 1:
                # process a cluster of short options (possibly with
                # value(s) for the last one only)
                self._process_short_opts(rargs)
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return                  # stop now, leave this arg in rargs

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                            ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)] and largs is a *subset* of
        # [arg0, ..., arg(i-1)] (any options and their arguments will have
        # been removed from largs).
        #
        # The while loop will usually consume 1 or more arguments per pass.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

    def _match_long_opt(self, opt):
        """_match_long_opt(opt : string) -> string

        Determine which long option string 'opt' matches, ie. which one
        it is an unambiguous abbrevation for.  Raises BadOptionError if
        'opt' doesn't unambiguously match any long option string.
        """
        # wordmap : {string : Option}
        wordmap = self._option_string_actions
        # this has both long and short, but that shouldn't matter
        return _match_abbrev(opt, wordmap)

    def _process_long_opt(self, rargs):
        arg = rargs.pop(0)

        # Value explicitly attached to arg?  Pretend it's the next
        # argument.
        if "=" in arg:
            (opt, next_arg) = arg.split("=", 1)
            rargs.insert(0, next_arg)
            had_explicit_value = True
        else:
            opt = arg
            had_explicit_value = False

        opt = self._match_long_opt(opt)
        action = self._option_string_actions[opt]
        nargs = self.opt_adapt_nargs(action.nargs, len(rargs))
        if nargs>0:
            if len(rargs) < nargs:
                self.error(ngettext(
                    "%(action)s option requires %(number)d argument",
                    "%(action)s option requires %(number)d arguments",
                    nargs) % {"action": opt, "number": nargs})
            elif nargs == 1:
                argument_strings = [rargs.pop(0)]
            else:
                argument_strings = rargs[0:nargs]
                del rargs[0:nargs]

        elif had_explicit_value:
            self.error(_("%s option does not take a value") % opt)
        else:
            argument_strings = []
        self.opt_take_action(action, argument_strings, self.namespace, opt)
        # return

    def _process_short_opts(self, rargs):
        arg = rargs.pop(0)
        stop = False
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            action = self._option_string_actions.get(opt, None)
            i += 1                      # we have consumed a character

            if not action:
                raise BadOptionError(opt)
            nargs = self.opt_adapt_nargs(action.nargs, len(rargs))
            if nargs>0:
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = True

                if len(rargs) < nargs:
                    self.error(ngettext(
                        "%(action)s option requires %(number)d argument",
                        "%(action)s option requires %(number)d arguments",
                        nargs) % {"action": opt, "number": nargs})
                elif nargs == 1:
                    argument_strings = [rargs.pop(0)]
                else:
                    argument_strings = rargs[0:nargs]
                    del rargs[0:nargs]

            else:                       # action doesn't take a value
                argument_strings = []

            self.opt_take_action(action, argument_strings, self.namespace, opt)

            if stop:
                break
    def opt_adapt_nargs(self, nargs, maxnargs):
        """translate argparse nargs to a optparse integer"""
        if nargs is None:
            return 1
        if isinstance(nargs, int):
            return nargs
        else:
            if nargs=='?':
                if maxnargs>0:
                    return 1
                else:
                    return 0
            elif nargs=='+':
                return maxnargs
            elif nargs=='*':
                return maxnargs
            else:
                raise OptParseError('')

    def opt_take_action(self, action, argument_strings, namespace, option_string=None):
        # option.process(opt, value, namespace, self)
        # take_action(action, argument_strings, option_string=None):
            # seen_actions.add(action)
            argument_values = self._get_values(action, argument_strings)

            # skip the mutually exclusive stuff

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not SUPPRESS:
                action(self, namespace, argument_values, option_string)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_argument("-f", "--file", dest="filename",
                  help="write report to FILE", metavar="FILE")
    parser.add_argument("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")

    parser.add_argument("--several", '-s', nargs='+', type=int,
                  default=[0,0])
    parser.add_argument('--int','-i', type=int, default='100')
    parser.add_argument('-c','--count', action='count',default=-1)
    parser.add_argument('foo',nargs='*', default='BOO',
                  help='positional that parse_opts cannot handle')

    print(parser.parse_opts('--file aname --quiet extra'.split()))
    print(parser.parse_opts('--file --quiet --count --cou'.split()))
    print(parser.parse_opts('--int=200 --several 1 2 3'.split())) # can't put -i last
    print(parser.parse_opts('-cs3 -cqfafile'.split()))
    try:
        parser.parse_opts('-h'.split())
    except SystemExit:
        print(_sys.exc_info()[1])
    print('')
    print(parser.parse_args('--file aname --quiet extra'.split()))
    try:
        print(parser.parse_args('--file --quiet --count'.split()))
    except SystemExit:
        print(_sys.exc_info()[1])
    print(parser.parse_args('--int=200 --several 1 2 3'.split())) # can't put -i last
    print(parser.parse_args('-cs3 -cqfafile'.split()))
    try:
        parser.parse_args('-h'.split())
    except SystemExit:
        print(_sys.exc_info()[1])
