import argparse

parent1 = argparse.ArgumentParser(add_help=False)
parent1.add_argument('--config')
parent2 = argparse.ArgumentParser(add_help=False)
parent2.add_argument('--config')

parser = argparse.ArgumentParser(parents=[parent1,parent2],
    conflict_handler='resolve')

def foo(parser):
    print ([(id(a), a.dest, a.option_strings) for a in parser._actions])

foo(parent1)
foo(parent2)
foo(parser)

print(parser.parse_args())

"""
[(3077384012L, 'config', [])]
[(3076863628L, 'config', ['--config'])]
[(3076864428L, 'help', ['-h', '--help']), (3076863628L, 'config', ['--config'])]
Namespace(config='3')

resolve - removed option_strings from parent1
matching id in parent2 and parser

Is this a bug in parents and/or resolve?
Or just a feature the requires documentation?
How is 'resolve' documented
How is 'parents' documented
"Sometimes (e.g. when using parents_) it may be useful to simply override any
older arguments with the same option string. "
but the example is two add_argument
(so this needs a fix or warning about the conflict altering the parent)


How about test_argparse?
'resolve' is tested only once, with:
        parser.add_argument('-x', help='OLD X')
        parser.add_argument('-x', help='NEW X')
'parents' has test for a optionals conflict between parents,
    and a positionals non-conflict between parents.



"""
