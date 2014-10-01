import argparse

action_copy = True
argparse._ActionsContainer._handle_conflict_resolve.action_copy = action_copy

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='cmd')
subcommand1 = subparsers.add_parser('subcommand1')
subcommand1.add_argument('--config', help="The config")

subcommand2 = subparsers.add_parser('subcommand2')
subcommand2.add_argument('--config', help="The config")

wrappercommand = subparsers.add_parser('wrappercommand',
                                       parents=[subcommand1, subcommand2],
                                       conflict_handler='resolve')

if action_copy:
    assert '--config' in subcommand1._actions[1].option_strings
else:
    assert len(subcommand1._actions[1].option_strings)==0

print(parser.parse_args())
