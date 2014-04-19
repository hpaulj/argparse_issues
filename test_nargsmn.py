import argparse
ArgumentParser = argparse.ArgumentParser

def exit(self, status=0, message=None):
    import sys
    #if message:
    #    self._print_message(message, sys.stderr)
    #sys.exit(status)
    raise Exception(message)
ArgumentParser.exit = exit


p=argparse.ArgumentParser()
p.add_argument('pos',nargs='{2,4}')
# print(p.parse_args('1'.split()))  # fail
print(p.parse_args('1 2'.split()))
# Namespace(pos=['1', '2'])
print(p.parse_args('1 2 3'.split()))
# Namespace(pos=['1', '2', '3'])
print(p.parse_args('1 2 3 4'.split()))
# Namespace(pos=['1', '2', '3', '4'])
print(p.parse_known_args('-foo 1 2 3 4'.split()))
# (Namespace(pos=['1', '2', '3', '4']), ['-foo'])
print(p.parse_known_args('-foo 1 2 3 4 bar'.split()))
# (Namespace(pos=['1', '2', '3', '4']), ['-foo', 'bar'])
print(p.format_usage())
# "usage: [-h] 'pos',{2,4}\n"
print(p.format_help())
# "usage: [-h] 'pos',{2,4}\n\npositional arguments:\n  pos\n\noptional arguments:\n  -h, --help  show this help message and exit\n"

p=argparse.ArgumentParser()
p.add_argument('pos',nargs='{2,}', metavar='POS')
print(p.parse_args('1 2'.split()))
# Namespace(pos=['1', '2'])
print(p.parse_args('1 2 3 4'.split()))
# Namespace(pos=['1', '2', '3', '4'])
print(p.parse_known_args('-foo 1 2 3 4 5 6'.split()))
# (Namespace(pos=['1', '2', '3', '4']), ['-foo'])
print(p.parse_known_args('-foo 1 2 3 4 bar'.split()))
# (Namespace(pos=['1', '2', '3', '4']), ['-foo', 'bar'])
print(p.format_usage())
# "usage: [-h] 'pos',{2,4}\n"

p=argparse.ArgumentParser()
p.add_argument('pos',nargs='{,2}')
print(p.parse_args([]))
# Namespace(pos=['1', '2'])
print(p.parse_args('1 2'.split()))
# Namespace(pos=['1', '2'])
print(p.parse_known_args('-foo 1 2 3 4'.split()))
# (Namespace(pos=['1', '2', '3', '4']), ['-foo'])
print(p.parse_known_args('-foo 1 2 3 4 bar'.split()))
# (Namespace(pos=['1', '2', '3', '4']), ['-foo', 'bar'])
print(p.format_usage())
# "usage: [-h] 'pos',{2,4}\n"

# test that '{8,3}' throws error during add_argument
# '{3,3}' also error
# test tuple style
p=argparse.ArgumentParser()
try:
    p.add_argument('--foo',nargs='{3,2}',type=int)
except Exception as e:
    print(repr(e))

p=argparse.ArgumentParser()
try:
    p.add_argument('--foo',nargs='{3,3}',type=int)
    print(p.format_usage())
    print(p.parse_args('--foo 1 2 3'.split()))
except Exception as e:
    print(repr(e))

p=argparse.ArgumentParser()
p.add_argument('foo',nargs=(2,4),type=int)
print(p.parse_args('1 2 3'.split()))

p=argparse.ArgumentParser()
p.add_argument('foo',nargs=(None,3),type=int)
print(p.parse_args(''.split()))

p=argparse.ArgumentParser()
p.add_argument('foo',nargs=(1,None),type=int)
print(p.parse_args('1 2'.split()))

# test _is_mnrep tweak that allow '{n}', sma as n
p=argparse.ArgumentParser()
p.add_argument('--foo',nargs='{3}',type=int)
print(p.format_usage())
print(p.parse_args('--foo 1 2 3'.split()))
try:
    print(p.parse_args('--foo 1 3'.split()))
except Exception as e:
    print('expected error with 2 args')