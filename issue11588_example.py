
import argparse
import sys
usage = '(-o FILE | (-O DIR & (-p PATTERN | -s SUFFIX))'
# usage = None
parser = argparse.ArgumentParser(usage=usage)
a_file= parser.add_argument("-o", "--outfile", metavar='FILE')
a_dir = parser.add_argument("-O", "--outdir", metavar='DIR')
a_pat = parser.add_argument("-p", "--outpattern", metavar='PATTERN')
a_suf = parser.add_argument("-s", "--outsuffix", metavar='SUFFIX')


def testwfnc(func):
    # decorator to facilitate adding these functions
    name = func.__name__
    def wrapped(parser, seen_actions, *args):
        # goal - make this function available inside func
        def seen(*args):
            # have these args been seen
            # handle either actions or dest str
            # should it take *args or args (which may be list, set etc?)
            actions = seen_actions
            if isinstance(args[0],str):
                actions = [a.dest for a in actions]
            if len(args)>1:
                return [a in actions for a in args]
            else:
                return args[0] in actions
        return func(parser, seen)
    parser.register('usage_tests', name, wrapped)
    return wrapped

#@testwfnc
def all_in_one(parser, seen, *args):
    if seen(a_file):
        print(seen(a_dir, a_pat, a_suf))
        cnt = sum(seen(a_dir, a_pat, a_suf))
        # len(seen_actions.intersection([a_dir, a_pat, a_suf]))
        if cnt>0:
            parser.error('FILE cannot have DIR, PATTERN or SUFFIX')
    elif seen(a_dir):
        cnt = seen(a_pat, a_suf)
        cnt = seen('outpattern','outsuffix') # alt
        #cnt = len(seen_actions.intersection([a_pat, a_suf]))
        if not any(cnt):
            parser.error('DIR requires PATTERN or SUFFIX')
        elif all(cnt):
            parser.error('cannot have both DIR and SUFFIX')
    else:
        parser.error('require FILE or DIR')

# make class with methods that simplify writing tests
import collections

class SeenActions(object):
    # class to facilitate inquiring whether an action has been 'seen'
    # is in the 'seen_list'
    # can handle quiries with Actions or 'dest' strings
    def __init__(self, seen_list):
        self.actions = seen_list
        self.dests = [a.dest for a in self.actions]
    def __contains__(self, arg):
        if isinstance(arg, str):
            return arg in self.dests
        else:
            return arg in self.actions
    def __len__(self):
        return len(self.actions)
    # does it make sense to write an __iter__ or next?
    def seen(self, args):
        # args can be any mix of action and dest(str)
        # args should be one item or iterable; return one value or list
        try:
            # otherwise return list if iterable
            return [a in self for a in args]
        except TypeError:
            return args in self
    def __call__(self, args):
        return self.seen(args)
    def count(self, arg):
        # how many times did this arg appear
        # use to test if arg occured only once
        # depends on 'actions' being a list
        actions = self.actions
        if isinstance(actions, set):
            # fudge if actions is a set
            actions = list(self.actions)
        return self.actions.count(arg)

    def intersection(self, args):
        return [a for a in args if a in self]


def testwobj(func):
    # decorator to facilitate adding these functions
    name = func.__name__
    def wrapped(parser, seen_actions, *args):
        seen = SeenActions(seen_actions)
        return func(parser, seen, *args)
    parser.register('usage_tests', name, wrapped)
    return wrapped
# decorator form if added to ArgumentParser
# def usagetest(self, func):
#    self.register('usage_tests', name, func)

@testwobj
def all_in_one(parser, seen, *args):
    print('all_in_one w/ obj decorator')
    #print(seen.actions)
    #print(seen.dests)
    if len(seen)==0:
        print('No SEEN actions')
        parser.print_help()
    # seen = seen.seen
    if a_file in seen:
        assert seen(a_file)
        others = [a_dir, a_pat, a_suf]
        cnt = sum(seen(others))
        if cnt>0:
            assert any(seen(others))
            assert len(seen.intersection(others))
            parser.error('FILE cannot have DIR, PATTERN or SUFFIX')
    elif a_dir in seen:
        cnt = seen([a_pat, a_suf])
        cnt = seen(['outpattern',a_suf]) # alt
        if not any(cnt):
            parser.error('DIR requires PATTERN or SUFFIX')
        elif all(cnt):
            parser.error('cannot have both DIR and SUFFIX')
    else:
        parser.error('require FILE or DIR')
@testwobj
def unique(parser, seen, *args):
    if seen.count(a_file)>1:
        parser.error('only one FILE allowed')

for test in [['-o FILE', ''],
             ['-O DIR -p PAT', ''],
             ['-O DIR -s SUF', ''],
             ['', 'require FILE or DIR'],
             ['-O DIR', 'DIR requires'],
             ['-o FILE -p PAT', 'FILE cannot'],
             ['-O DIR -o FILE', 'FILE cannot'],
             ['-O DIR -p PAT -s SUF', 'cannot have both'],
             ['-o FILE1 -o FILE2', 'only one'],
             ]:
    print(test[0])
    try:
        print(parser.parse_args(test[0].split()))
    except SystemExit:
        assert len(test[1])>0
        pass
    print()

@testwobj
def test_mut_ex_groups(parser, seen, *args):
    # alternative mutually_exclusive_groups test
    for group in parser._mutually_exclusive_groups:
        group_actions = group._group_actions
        group_seen = seen(group_actions)
        cnt = sum(group_seen)
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
