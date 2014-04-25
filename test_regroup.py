import argparse

p = argparse.ArgumentParser()

def testalt(args=None):
    p.prog = 'orig'
    p.formatter_class = argparse.HelpFormatter
    print(p.format_usage())
    p.prog = 'regp'
    p.formatter_class = argparse.ReGroupHelpFormatter
    print(p.format_usage())
    for arg in args:
        print(p.parse_args(arg.split()))

g=p.add_mutually_exclusive_group()
g.add_argument('--opt1')
g.add_argument('opt2',nargs='?')

p.add_argument('foo')
p.add_argument('arg1',nargs='?')
a = p.add_argument('arg2',nargs='?')
print('with MXG')
testalt(['A B C'])

print('================')
p = argparse.ArgumentParser()
p.add_argument('foo')
p.add_argument('arg1',nargs='?')
p.add_argument('arg2',nargs='?')
a = p.add_argument('arg3',nargs='*')
b = p.add_argument('arg4', nargs='?')
print('with *')
# usage: regp [-h] foo [arg1 [arg2 [arg3 [arg3 ...] [arg4]]]]

testalt(['A B C','A B C D','A B C D E'])
print("============")
a.nargs = '+'
print('with +')

# usage: regp [-h] foo [arg1 [arg2]] arg3 [arg3 ...] [arg4]
testalt(['A B C','A B C D','A B C D E'])
print("=========")

p = argparse.ArgumentParser(prefix_chars='+*')
p.add_argument('+test')
p.add_argument('arg1',nargs='?')
p.add_argument('arg2',nargs='?')
p.add_argument('*bar',action='store_true')
testalt([])
