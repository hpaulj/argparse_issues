from sample3 import *

parent1 = argparse.ArgumentParser(prog='parent1', add_help=False)
parent1.add_argument('--config', help='parent1 config')
parent2 = argparse.ArgumentParser(prog='parent2', add_help=False)
parent2.add_argument('--config', help='parent2 config')

parser = argparse.ArgumentParser(prog='PROG', parents=[parent1,parent2],
    conflict_handler='parent')

display(parent1)

display(parent2)
display(parser)

if parser.conflict_handler=='resolve':
    # resolve removess
    assert parent1._actions[0].option_strings==[]
elif parser.conflict_handler=='parent':
    assert parent1._actions[0].option_strings==['--config']
    assert len(parser._actions[1].containers)==2
assert parser._actions[1].help=='parent2 config'

parser.print_help()

print('\n---------------------------\nhttp://stackoverflow.com/questions/25818651\n')
parser = argparse.ArgumentParser(prog='PROG')
subparsers = parser.add_subparsers(dest='cmd')
subcommand1 = subparsers.add_parser('subcommand1')
subcommand1.add_argument('--config', help="The config")

subcommand2 = subparsers.add_parser('subcommand2')
subcommand2.add_argument('--config', help="The config")

wrappercommand = subparsers.add_parser('wrappercommand',
                                       parents=[subcommand1, subcommand2],
                                       conflict_handler='parent',
                                       #add_help=False,  # handler takes care of this
                                       )
print()
display(subcommand1)
display(subcommand2)
display(wrappercommand)

if parser.conflict_handler=='resolve':
    # resolve removes
    assert subcommand1._actions[0].option_strings==[] # help
    assert subcommand1._actions[1].option_strings==[] # config
elif wrappercommand.conflict_handler=='parent':
    assert subcommand1._actions[0].option_strings==['-h', '--help']
    assert subcommand1._actions[1].option_strings==['--config']
    assert len(wrappercommand._actions[1].containers)==2
assert wrappercommand._actions[1] is subcommand2._actions[1]

print(parser.parse_args('wrappercommand -h'.split()))
