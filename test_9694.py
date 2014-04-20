import argparse
p = argparse.ArgumentParser(help_groups=['positionals','other'])
p.add_argument('--foo')
sp = p.add_subparsers()#title='subparsers')
sp1 = sp.add_parser('cmd1')
sp1.add_argument('bar')
sp2 = sp.add_parser('cmd2',help_groups=['pos','req','opt'])
sp2.add_argument('baz')
sp2.add_argument('--bar', required=True)
p.print_help()
sp1.print_help()
sp2.print_help()
print(p.parse_args())


p = argparse.ArgumentParser()
p.add_argument('x')
g = p.add_mutually_exclusive_group()
#g = p.add_argument_group(title='xxx')
g.add_argument('-f')
g.add_argument('-g')
p.print_help()
print(p.parse_args([]))
