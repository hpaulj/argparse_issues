import argparse
action_copy = False
# print(argparse._ActionsContainer._handle_conflict_resolve.action_copy)
argparse._ActionsContainer._handle_conflict_resolve.action_copy = action_copy

# this is the top level parser
parser = argparse.ArgumentParser(description='bla bla')

# this serves as a parent parser
base_parser = argparse.ArgumentParser(add_help=False)
base_parser.add_argument('-n', help='number', type=int)


# subparsers
subparsers = parser.add_subparsers()
subparser1= subparsers.add_parser('a', help='subparser 1',
                                   parents=[base_parser],
                                   conflict_handler='resolve')
subparser1.set_defaults(n=50)
subparser2 = subparsers.add_parser('b', help='subparser 2',
                                   parents=[base_parser],
                                   conflict_handler='resolve')
subparser2.set_defaults(n=20)

args = parser.parse_args(['a'])
print(args)
assert args.n == 50 if action_copy else 20
args = parser.parse_args(['b'])
print(args)

# without actions_copy, the 2nd set_defaults overrides the 1st
# default parent action is copy by refererence
