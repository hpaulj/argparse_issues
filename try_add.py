import argparse

parent = argparse.ArgumentParser()
parent.add_argument('-f')
parent.add_argument('bar')

parser = argparse.ArgumentParser()
sp = parser.add_subparsers(dest='cmd')
p1 = sp.add_parser('cmd1', add_help=False, parents=[parent])
p2 = sp.add_parser('cmd2', parser=parent)
parent.add_argument('test')
assert p2 is parent
assert p1 is not parent
print(parser.parse_args())