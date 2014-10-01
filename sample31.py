"""
Trial of a custom handle_conflict method, that gets around the limitions of
'resolve' when handling parents.

Use actions_copy
Not containers

"""

import argparse, sys
import logging
import io

logging.basicConfig()#level=0, format='log %(levelno)s:%(message)s')

def debug_parser(p):
    # custom display of a parser and its actions
    # format string to write to log
    logger=logging.getLogger('{} {}'.format(p.prog, id(p)))
    astr = """
     option_strings: {}
     groups: {}
     actions:\n"""
    astr = astr.format(list(p._option_string_actions.keys()),
        [(g.title, id(g)) for g in p._action_groups])
    for a in p._actions:
        aastr = io.StringIO()
        print('      ',(a.dest, a.option_strings, (a.container.title, id(a.container))), id(a),file=aastr)
        aastr = aastr.getvalue()
        astr += aastr
    logger.debug(astr)

def define(args):
    # create a parser with subparsers and parent
    # a complex mix of argument conflicts
    #do_copy = args.do_copy
    #argparse._ActionsContainer._handle_conflict_resolve.action_copy = do_copy

    handler = 'resolve'#args.handler
    parent = argparse.ArgumentParser(add_help=False, prog='PARENT',
                conflict_handler=handler)
    parent_group = parent.add_argument_group(title='group')
    parent_opt = parent_group.add_argument('-o','--opt', '--other', default='parent',
                help='parent opt', dest='parent_opt', metavar='Opt')
    parent_foo = parent_group.add_argument('-f', '--foo', help='parent help')

    debug_parser(parent)

    parser = argparse.ArgumentParser(prog='PROG')
    sp = parser.add_subparsers(dest='cmd')

    print('\nsubparser cmd1 inherit from parent:')
    cmd1 = sp.add_parser('cmd1', parents=[parent], conflict_handler=handler)
    cmd1_opt = cmd1.add_argument('--opt','-o', default='parser', help='cmd1 opt')
    # this --opt overrides the --opt from parent - but they are in diff groups

    cmd1.add_argument('-o', '--orange') # partial conflict

    print('\nadd foobar to parent:')
    foobar = parent_group.add_argument('-f', '--foobar')

    print('\nsubparser cmd2 inherit from parent')
    cmd2 = sp.add_parser('cmd2', parents=[parent])

    debug_parser(cmd1)
    print('\nadd foo to cmd1')
    cmd1.add_argument('-f', '--foo', help='cmd1 help')

    assert len(parent._actions)==3, "['parent_opt', 'foo', 'foobar']"
    assert len(cmd1._actions)==5, "['help', 'parent_opt', 'opt', 'orange', 'foo']"
    assert len(cmd2._actions)==4, "['help', 'parent_opt', 'foo', 'foobar']"

    debug_parser(parent)
    debug_parser(cmd1)
    debug_parser(cmd2)
    debug_parser(parser)

    return parser, parent, cmd1, cmd2

def parse(opts, argv, parsers):
    # run parser, display various diagnostics
    lvl = logging.getLogger().getEffectiveLevel()
    parser, parent, cmd1, cmd2 = parsers
    #do_copy = opts.do_copy # parent.do_copy

    args = parser.parse_args(['cmd1'])
    if lvl<30: print(args)
    expt = argparse.Namespace(cmd='cmd1', foo=None, opt='parser', orange=None, parent_opt='parent')
    assert args == expt
    args = parser.parse_args(['cmd2'])
    if lvl<30: print(args)
    expt = argparse.Namespace(cmd='cmd2', foo=None, foobar=None, parent_opt='parent')
    assert args == expt

    if lvl<30:
        print()
        cmd1.print_help()
        print()
        cmd2.print_help()
    print(parser.parse_args(argv))
    print()

if __name__ == '__main__':
    p = argparse.ArgumentParser(prog='main')
    p.add_argument('-l','--logging', type=int, default=40, help='logging level, smaller means more')
    args, rest = p.parse_known_args()

    logging.getLogger().setLevel(args.logging)
    parse(args, rest, define(args))

"""


"""

