__version__ = '0.0.0'

from contextlib import redirect_stdout

class ReDict(dict):
    def __getitem__(self, pattern):
        for key, value in self.items():
            if re.search(pattern, key): return value
        return super().__getitem__(pattern)

    def get_reverse(self, pattern):
        try:
            for key, value in self.items():
                if re.search(key, pattern): return value
            return super().__getitem__(pattern)
        except: return '__notfound__'

    def pop(self, pattern, default):
        try: return self[pattern]
        except: return super().pop(pattern, default)

    def pop_reverse(self, pattern, default):
        try: return self.get_reverse(pattern)
        except: return super().pop(pattern, default)

# from .trace import *
# from .message import *
# from .logger import *
# __all__ = ['Logger', 'Message', 'Header', 'SourceFromFilenameAndLineno',
# 'SourceFromTraceback']

from .logging import Header
from .logging import Log
# from .logging import Message
# from .logging import StringVar
from .logging import strvar

def debugger():
    debuggers = []
    from .debugger1 import Debugger
    debuggers.append((Debugger()))
    from .debugger2 import Debugger
    debuggers.append(Debugger(debuggers[-1]))
    from .debugger3 import Debugger
    debuggers.append(Debugger(debuggers[-1]))
    from .debugger4 import Debugger
    debuggers.append(Debugger(backup_debugger=debuggers[-1]))
    return debuggers[-1]

# print('debug being imported')


log = Log(
    # use_stdout=False,
)
log.class_ens = ReDict({
    'Debugger': False,
    'SourceMessage': False,
    'Debuggers': True,
    'Utils': False,

    # 'Counter': False,
    # 'ATilerTest': True,
    # 'Space': False,
    # 'TilerTest': True,
    # 'Tiler': False,
    # 'MetaTree': False,
})

# log.local_class_ens = ReDict({
#     'Space': True,
# })
log.max_nof_lines = 10000
log.infolevel = 'mid'
# log.rm()
# log.infolevel = 'high'
# log.prefix = '--> '

# dlog = Log(file='*compilation*', banner_en=False,
dlog = Log(
    # file='*outlog2*',
    files=[],
    # use_stdout=False,
    banner_en=False,
           prefix='',
           class_ens={},
           value_only=True)
dlog.max_nof_lines = 20


def log2(s='\n', file=log.files[0]):
    with open(file, 'a') as f:
        with redirect_stdout(f):
            print(str(s))


from .debug import Debug
