# 3, 4, 5 correct

import argparse, sys
print(sys.argv)
test = int(sys.argv[1])
sys.argv[1:] = sys.argv[2:]
print(sys.argv)

def foo0():
    print('(--arg ARGUMENT & {-a A | -b B})')
    # arg and (a or b)
    # non raise error on nested
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind='and')
    g1.add_argument('--arg', metavar='C')
    g2 = g1.add_usage_group(kind='or')
    g2.add_argument('-a')
    g2.add_argument('-b')
    return p

def foo1():
    # test for each of the allowed combinations
    print('4 ands')
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind='or', dest='any()', required=True)
    g11 = g1.add_usage_group(kind='and', dest='and1') # a, not arg
    g12 = g1.add_usage_group(kind='and', dest='and2') # b, not arg
    g13 = g1.add_usage_group(kind='and', dest='and3') # all 3
    g14 = g1.add_usage_group(kind='not', dest='none') # none

    not_arg = g11.add_usage_group(kind='not')
    arg = not_arg.add_argument('--arg', metavar='C')
    a = g11.add_argument('-a')

    g12.add_usage_group(not_arg)
    b = g12.add_argument('-b')

    g13.add_argument(arg)
    g13.add_argument(a)
    g13.add_argument(b)

    g141 = g14.add_usage_group(kind='or')
    g141.add_argument(arg)
    g141.add_argument(a)
    g141.add_argument(b)

    try:
        argparse.UsageGroup.tree(p)
    except AttributeError:
        pass
    return p

def foo1():
    # test for each of the allowed combinations
    print('3 ands')
    # consolidate 2 groups from the previous
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind='any', dest='any()', required=True)

    g11 = g1.add_usage_group(kind='and', dest='and1')
    not_arg = g11.add_usage_group(kind='not')
    arg = not_arg.add_argument('--arg', metavar='C')
    g111 = g11.add_usage_group(kind='or')
    a = g111.add_argument('-a')
    b = g111.add_argument('-b')

    g12 = g1.add_usage_group(kind='and', dest='and2') # all 3
    g12.add_argument(arg)
    g12.add_argument(a)
    g12.add_argument(b)

    g13 = g1.add_usage_group(kind='not', dest='none') # none
    g131 = g13.add_usage_group(kind='any')
    g131.add_argument(arg)
    g131.add_argument(a)
    g131.add_argument(b)
    # would be nice if groups could takes multiple arguments
    # eg g131.add_argument([arg, a, b])
    # or
    # g131 = g13.add_usage_group(kind='any', arguments=[arg, a, b])

    try:
        argparse.UsageGroup.tree(p)
    except AttributeError:
        pass
    return p

def foo2():
    print('not')
    # try not on OP test
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind='not', required=True)
    g1and = g1.add_usage_group(kind='and')
    arg = g1and.add_argument('--arg', metavar='C')
    g11or = g1and.add_usage_group(kind='or')
    g11a = g11or.add_usage_group(kind='not')
    g11a.add_argument('-a')
    g11b = g11or.add_usage_group(kind='not')
    g11b.add_argument('-b')

    try:
        argparse.UsageGroup.tree(p)
    except AttributeError:
        pass

    return p

def foo2():
    print('not')
    # try not on OP test
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind='not', required=True)
    g1and = g1.add_usage_group(kind='and')
    arg = g1and.add_argument('--arg', metavar='C')
    # rewrite or(not,not) as not(and(,) (nand)
    g11not = g1and.add_usage_group(kind='not')
    g11and = g11not.add_usage_group(kind='and')
    g11and.add_argument('-a')
    g11and.add_argument('-b')

    try:
        argparse.UsageGroup.tree(p)
    except AttributeError:
        pass

    return p

def foo6():
    print('nand')
    # try not on OP test
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind='nand', dest='nand1')
    arg = g1.add_argument('--arg', metavar='C')
    g11 = g1.add_usage_group(kind='nand', dest='nand2')
    g11.add_argument('-a')
    g11.add_argument('-b')

    try:
        argparse.UsageGroup.tree(p)
    except AttributeError:
        pass

    return p


def foo3():
    print('class Test - custom usage class like OP test')
    class Test(argparse.UsageGroup):
        def _add_test(self):
            self.usage = '(if --arg then -a and -b are required)'
            def testfn(parser, seen_actions, *vargs, **kwargs):
                "custom error"
                actions = self._group_actions
                if actions[0] in seen_actions:
                    if actions[1] not in seen_actions or actions[2] not in seen_actions:
                        msg = '%s - 2nd and 3rd required with 1st'
                        self.raise_error(parser, msg)
                return True
            self.testfn = testfn
            self.dest = 'Test'
    p = argparse.ArgumentParser(formatter_class=argparse.UsageGroupHelpFormatter)
    g1 = p.add_usage_group(kind=Test)
    g1.add_argument('--arg', metavar='C')
    g1.add_argument('-a')
    g1.add_argument('-b')
    return p

def foo4():
    print('OP - post parse test')
    p = argparse.ArgumentParser(description='...')
    p.add_argument('--arg', metavar='C', required=False)
    p.add_argument('-a', required=False) # only required if --arg is given
    p.add_argument('-b', required=False) # only required if --arg is given
    def parse(argv):
        args, extras = p.parse_known_args(argv)
        if args.arg and (args.a is None or args.b is None):
            p.error('with arg require a and b')
        return args
    p.parse_args = parse
    return p

def foo5():
    print('CondAction - changes required attribute on fly')
    class CondAction(argparse._StoreAction):
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            x = kwargs.pop('to_be_required', [])
            super(CondAction, self).__init__(option_strings, dest, **kwargs)
            self.make_required = x

        def __call__(self, parser, namespace, values, option_string=None):
            for x in self.make_required:
                x.required = True
            return super(CondAction, self).__call__(parser, namespace, values, option_string)

    p = argparse.ArgumentParser()
    a = p.add_argument("-a")
    b = p.add_argument("-b")
    p.add_argument("--arg", metavar='C', action=CondAction, to_be_required=[a,b])
    return p

tests = [foo0, foo1, foo2, foo3, foo4, foo5, foo6]
p = tests[test]()

if sys.argv[2:]:
    print(p.parse_args())
else:
    args = ['','-a1','-a1 -b2','--arg=3 -a1 -b2','--arg=3','--arg=3 -a1','--arg=3 -b2']
    for a in args:
        try:
            print(a, file=sys.stderr)
            print(p.parse_args(a.split()))
        except SystemExit:
            print('error:', a)
            pass
