"""
Trial of a custom handle_conflict method, that gets around the limitions of
'resolve' when handling parents.

'resolve' is trying to be too smart - it removes conflicting option_strings
without removing the action itself.  Only if all the strings conflict does it remove
the action itself.  This is fine if the action was created by this parser.
But if the action came from a parent, it ends up modifying the original,
breaking the parent parser.

This custom handler distinguishes between actions that came from a parent from
ones created here (using an attribute set by _add_container_actions).  If
the action came from a parent, it is simply removed from self (along with all
of its option_strings).

An complication is an action has only one .container attribute, with points to
the last group that was added to.  But that might not be the current parser (and group)
where the conflict is occuring.  Unfortunately argument_groups do not have a record
of their parser (a fault which maybe should be corrected).  Fortunately,
_add_container_actions() knows this, and can add it to a '.containers' attribute.
So this handler has a nested function to match groups and return the correct
argument group (and a 'multiple' boolean).

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
        containers = getattr(a,'containers',None)
        if containers:
            print('         containers:',[(g[0].prog, g[1].title, id(g[1])) for g in containers],file=aastr)
        aastr = aastr.getvalue()
        astr += aastr
    logger.debug(astr)

def _handle_conflict_parent(self, new_action, conflicting_actions):
    # remove all conflicting options
    # removes a conflicting action along with all its option_strings
    # here new_action is not used, except for diagnostic display
    # (new_action may not have a .container at this point, since it has not been added to self yet).
    logger = logging.getLogger('Parent')
    def find_parser(self, action):
        # find 'action' container that is in the same parser as 'self'
        # returns 'multiple' boolean, correct container (group)
        container = action.container
        containers = getattr(action, 'containers', None)
        if containers is None:
            return 1, container
        logger.info('    containers: {}'.format([(id(pg[0]), id(pg[1])) for pg in containers]))
        found = False
        for parser, group in containers:
            if self in parser._action_groups:
                # shared parser, the correct group
                if group is not action.container:
                    logger.info('    changing container')
                    container = group
                found = True
                break
        if found:
            logger.info('    parser: {} {}'.format(id(parser), parser.prog))
        else:
            return len(containers), None
        return len(containers), container

    def remove_action(action, container):
        # remove action from container
        # also remove container from action's containers list
        container._remove_action(action)
        if hasattr(action, 'containers'):
            for i, g in enumerate(action.containers):
                if g[1] is container:
                    del action.containers[i]
                    if len(action.containers)>0:
                        logger.info('    deleted container: {0[0].prog!r} from {1}'.format(g, id(action)))
                    break
            if len(action.containers)>0 and not action.option_strings:
                # correct use of resolve should prevent this error
                assert False, 'Action in parser with no option_strings'

    logger.info("conflict call group: {0.title!r}, {1}; action:{2.dest!r}".format(self, id(self), new_action))
    for option_string, action in conflicting_actions:
        logger.info("  conflicting: {0!r} {1.dest!r}".format(option_string, action))
        count, container = find_parser(self, action)
        if container is None:
            logger.info('  no matching parser')
            continue
        if count>1:
            # this action is found in multiple containers (groups), probably via parent(s)
            # remove it and its option_strings; do not alter the action (or other parsers)
            if action in container._actions:
                remove_action(action, container)
                for s in action.option_strings:
                    self._option_string_actions.pop(s, None)
                logger.info("    removed action: '{0.title}({1}):{2.dest}'".format(container, id(container), action))
                logger.info('    removed strings:{}'.format(action.option_strings))
            else:
                pass # already removed
        else:  # count==1
            # action is in only one container; it is safe to perform a partial removal
            # remove just the conflicting option_strings
            logger.info('   using resolve: {}'.format((option_string, action.dest, id(action))))
            action.option_strings.remove(option_string)
            self._option_string_actions.pop(option_string, None)
            if not action.option_strings:
                remove_action(action, container)

# handlers are methods of the Container class (not of the parser)
# adding a custom handler is messier than adding custom types or action
argparse._ActionsContainer._handle_conflict_parent = _handle_conflict_parent

def _handle_conflict_resolve(self, new_action, conflicting_actions):
    logger = logging.getLogger('Resolver')
    logger.info("conflict call group: {0.title!r}, {1}; action:{2.dest!r}".format(self, id(self), new_action))
    # remove all conflicting options
    for option_string, action in conflicting_actions:
        logger.info(( option_string, action.dest, id(action)))
        # remove the conflicting option
        action.option_strings.remove(option_string)
        self._option_string_actions.pop(option_string, None)

        # if the option now has no option string, remove it from the
        # container holding it
        if not action.option_strings:
            action.container._remove_action(action)
            if hasattr(action, 'containers'):
                for i, g in enumerate(action.containers):
                    if g[1] is action.container:
                        del action.containers[i]
                        if len(action.containers)>0:
                            logger.info('    deleted container: {0[0].prog!r}'.format(g))
                        break
                if len(action.containers)>0:
                    logger.warn('action with no option_strings', lvl=30)

argparse._ActionsContainer._handle_conflict_resolve = _handle_conflict_resolve


# change this to record the 'containers'
def _add_container_actions(self, container):
    logger = logging.getLogger('AddContainer')
    # collect groups by titles
    title_group_map = {}
    for group in self._action_groups:
        if group.title in title_group_map:
            msg = _('cannot merge actions - two groups are named %r')
            raise ValueError(msg % (group.title))
        title_group_map[group.title] = group
    # print(title_group_map) # most likely just the default optionals and positionals
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
            # print('created group', group.title)
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
        # add a 'containers' attribute to keep track of all the groups that contain this action
        # record the parser (here 'container') as well as the argument_group
        # this is necessary because argument_groups do not have a 'parser' attribute

        do_copy = getattr(container, 'do_copy', False)
        # who should have a copy flag, the parser or the action? or someone else?
        if do_copy:
            new_action = action.copy()
            group_map.get(action, self)._add_action(new_action)
            new_action.containers = [(self, new_action.container)]
            # .container is set by _add_action
            # .containers is the same, without any of action's history
            logger.info(' making a copy %s'%[action.dest, id(action), id(new_action)])

        else:
            action.containers = getattr(action, 'containers', [(container, action.container)])
            group_map.get(action, self)._add_action(action)
            action.containers.append((self,action.container))

argparse._ActionsContainer._add_container_actions = _add_container_actions



def action_copy(self):
    # make a copy of self that can be changed without affecting self
    from copy import copy
    action = copy(self)
    action.option_strings = self.option_strings.copy()
    # any other attributes need to copied?  Most are strings
    return action
argparse.Action.copy = action_copy # add to base Action class

def define(args):
    # create a parser with subparsers and parent
    # a complex mix of argument conflicts
    do_copy = args.do_copy
    handler = args.handler
    parent = argparse.ArgumentParser(add_help=False, prog='PARENT',
                conflict_handler=handler)
    parent_group = parent.add_argument_group(title='group')
    parent_opt = parent_group.add_argument('-o','--opt', '--other', default='parent',
                help='parent opt', dest='parent_opt', metavar='Opt')
    parent_foo = parent_group.add_argument('-f', '--foo', help='parent help')
    # parent_group.add_argument('-f', '--foobar')  # does a resolve here

    # parent.add_argument('pos', help='parent help')
    parent.do_copy = do_copy  # test an action copy mechanism
    debug_parser(parent)

    parser = argparse.ArgumentParser(prog='PROG')
    sp = parser.add_subparsers(dest='cmd')

    print('\nsubparser cmd1 inherit from parent:')
    cmd1 = sp.add_parser('cmd1', parents=[parent], conflict_handler=handler)
    cmd1_opt = cmd1.add_argument('--opt','-o', default='parser', help='cmd1 opt')
    # this --opt overrides the --opt from parent - but they are in diff groups

    # cmd1.add_argument('--foo', help='cmd1 help')
    # cmd1.add_argument('pos', help='cmd1 help')
    cmd1.add_argument('-o', '--orange') # partial conflict

    print('\nadd foobar to parent:')
    foobar = parent_group.add_argument('-f', '--foobar')  # try changing parent between uses
    # does a replace here, because --foo now is in 2 containers (original parent and cmd1)
    if not do_copy:
        assert len(parent_foo.containers)==1  # removed from parent, left in cmd1
    else:
        assert not hasattr(parent_foo, 'containers')
        # this action is the original

    print('\nsubparser cmd2 inherit from parent')
    cmd2 = sp.add_parser('cmd2', parents=[parent])

    # try an 'out of order' conflict
    # ensure it is changing the correct parser
    # with partial resolve, -f for parent_foo, --foo for this
    #
    debug_parser(cmd1)
    print('\nadd foo to cmd1')
    cmd1.add_argument('-f', '--foo', help='cmd1 help')

    if not do_copy:
        assert len(parent._actions)==2, 'parent should have "parent_opt", "foobar" actions'
        assert len(cmd1._actions)==4, "[help, opt, orange, foo]"
        assert len(cmd2._actions)==3  # help, parent_opt, foobar
        assert all([a in cmd2._actions for a in parent._actions])
        # all parent's have been copied to cmd2
        assert all([a not in cmd1._actions for a in parent._actions])
        # all parent's have been overridden in cmd1
        assert len(foobar.containers)==2
        assert len(parent_opt.containers)==2 # parent, cmd2
        # this should have been removed from cmd1
        print('parent_foo containers:', len(parent_foo.containers))
        print([(g[0].prog, g[1].title) for g in parent_foo.containers])
        # parent_foo should have no containers - it's been deleted from all, and
        # now only exists as this global variable
    else:
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
    do_copy = opts.do_copy # parent.do_copy

    args = parser.parse_args(['cmd1'])
    if lvl<30: print(args)
    if not do_copy:
        expt = argparse.Namespace(cmd='cmd1', foo=None, opt='parser', orange=None)
    else:
        expt = argparse.Namespace(cmd='cmd1', foo=None, opt='parser', orange=None, parent_opt='parent')
    assert args == expt
    args = parser.parse_args(['cmd2'])
    if lvl<30: print(args)
    if not do_copy:
        expt = argparse.Namespace(cmd='cmd2', foobar=None, parent_opt='parent')
    else:
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
    p.add_argument('-c','--do_copy', action='store_true', help='copy actions from parent')
    h=p.add_argument('--handler', choices={'error','resolve','parent'}, default='parent')
    p.add_argument('-l','--logging', type=int, default=40, help='logging level, smaller means more')
    args, rest = p.parse_known_args()

    logging.getLogger().setLevel(args.logging)
    parse(args, rest, define(args))

"""
usage: PROG cmd1 [-h] [--opt OPT] [-o ORANGE] [--foo FOO]

optional arguments:
  -h, --help            show this help message and exit
  --opt OPT             cmd1 opt
  -o ORANGE, --orange ORANGE
  --foo FOO             cmd1 help

------------------
usage: PROG cmd2 [-h] [-o Opt] [-f FOOBAR]

optional arguments:
  -h, --help            show this help message and exit

group:
  parent group

  -o Opt, --opt Opt, --other Opt
                        parent opt
  -f FOOBAR, --foobar FOOBAR

"""

