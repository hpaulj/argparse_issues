import argparse
parser=argparse.ArgumentParser()
parser=argparse.ArgumentParser(formatter_class=argparse.MultiGroupHelpFormatter)
g1=parser.add_mutually_exclusive_group(title='test group')
fooAction = g1.add_argument('--foo')
g2=parser.add_mutually_exclusive_group()
barAction = g2.add_argument('--bar')
g2.add_argument(fooAction) # with MXG extension
parser.print_help()
print(parser.parse_args('--foo xxx --bar xxx'.split()))