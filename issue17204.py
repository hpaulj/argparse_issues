import argparse

parser = argparse.ArgumentParser(prog='PROG')
subparsers = parser.add_subparsers(dest='cmd')

proto1 = argparse.ArgumentParser(prog='SUBPROG1')
proto1.add_argument('--foo')
proto2 = argparse.ArgumentParser(prog='SUBPROG2')
proto2.add_argument('--bar')
# print(subparsers._parser_class)

class CustomParser(argparse.ArgumentParser):
    def __init__(self, **kwargs):
        super(CustomParser,self).__init__()
        for k,v in vars(kwargs['proto']).items():
            setattr(self,k,v)

subparsers._parser_class = CustomParser
subparsers.add_parser('cmd1', proto=proto1, help='parser based on proto1')
subparsers.add_parser('cmd2', proto=proto2, help='parser based on proto2')
print(parser.parse_args())

