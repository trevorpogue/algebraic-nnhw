__all__ = ['Debugger']
import sys
# import inspect
import traceback
import re
from varname.helpers import debug
# from ..utils._args2attrs import _args2attrs
import inspect
# from src.debug.logger import log
import copy
import math
from inspect import signature

def ___update_if_present(d2update, d2pass, name, d2check=None):
    if d2check is None: d2check = d2pass
    try:
        dummy = d2check[name]
        d2update[name] = d2pass[name]
        ret = True
    except: ret = False
    return ret

def _args2attrs(*dec_names, **dec_bindings):
    def decorator(method, ):
        def wrapper(self, *passed_args, **passed_kwds):
            params = signature(method).parameters

            names = {}
            bindings2pass = {}

            """get all attr names to be assigneb"""
            for name in dec_names: dec_bindings[name] = None

            for name in params: names[name] = True
            for name in dec_bindings: names[name] = True
            self_name = next(iter(names))
            names.pop(self_name, None)
            attrs2update = dict.fromkeys(dec_bindings if  dec_bindings
                                         else names, True)
            attrs2update.pop(self_name, None)

            # TODO: pop self_name in params then simplify below
            for i, (name, param) in enumerate(params.items(), -1):
                """get attr values from all scopes"""
                # debug(name)
                if name is self_name: continue
                if i < len(passed_args):
                    bindings2pass[name] = passed_args[i]
                else:
                    try: bindings2pass[name] = passed_kwds[name]
                    except: bindings2pass[name] = param.default


            attr_bindings = {}
            for name in attrs2update:
                # try:
                ___update_if_present(attr_bindings, dec_bindings, name)
                ___update_if_present(attr_bindings, bindings2pass, name)

            for name in attr_bindings:
                # debug(name)
                # debug(attr_bindings[name])
                setattr(self, name, attr_bindings[name])
                # debug(getattr(self, name))
                # except: pass


            # debug(dec_bindings)
            # debug(bindings2pass)
            # debug([*names.keys()])
            # debug([*attrs2update.keys()])
            # debug(passed_args)
            # debug(passed_kwds)
            # debug(attr_bindings)
            # debug(bindings2pass)
            # print()

            return method(self, **bindings2pass)

        return wrapper
    return decorator

class _Message():
    # _verbose_init_keys=('prefix', 'body', 'suffix', )
    # _verbose_init_keys={'prefix':'', 'body':'', 'suffix':'', }
    _verbose_init_keys = dict(prefix='', body='', suffix='', )
    @_args2attrs(**_verbose_init_keys)
    def __init__(self, prefix_body_suffix=None, splitter=','):
    # def __init__(self, prefix_body_suffix=None, prefix='', body='',
                 # suffix='', splitter=None):

        if prefix_body_suffix:
            self.split_init(prefix_body_suffix, splitter)
        # debug(self.__dict__)
        super().__init__()

    # @logargs()
    def split_init(self, prefix_body_suffix, split_str=','):
        attrs_found = {}
        for name, value in zip(self._verbose_init_keys,
                          prefix_body_suffix.split(split_str)):
            if value is not None:
                attrs_found[name] = value
        #
        # if attx
        for name, value in attrs_found.items():
            setattr(self, name, value)
        #
        return bool(attrs_found)

    @property
    def message(self, ): return self.body
    @message.setter
    def message(self, value): self.body = value

    @property
    def name(self, ): return self.body
    @name.setter
    def name(self, value): self.body = value

    # @_args2attrs()
    def update(self, body): self.body = body

    def __str__(self):
        return self.prefix + self.body + self.suffix

    def __eq__(self, other):
        return self.body == other

    @property
    def copy(self): return copy.deepcopy(self)

    @property
    def str(self): return f'{self.copy}'

    def __call__(self, body=None):
        if body:
            orig_body = self.body
            self.body = body
        str_ = self.str
        if body: self.body = orig_body
        return str_
    # @str.setter
    # def str(self, s):
        # self.


class _Header(_Message):
    default_symbol = '_'

    @_args2attrs('width')
    def __init__(self, *args, width=79,**kwds):
        self.symbol = self.default_symbol
        super().__init__(*args, **kwds)

    @property
    def prefix_suffix_len(self): return len(self.prefix) + len(self.suffix)
    @property
    def body_len(self): return self.width - self.prefix_suffix_len
    @property
    def n_body_units(self): return math.floor(self.width / len(self._symbol))\
            - self.prefix_suffix_len
    # def n_body_units(self):
        # if len(self._symbol) > 0:
            # return math.floor(self.width / len(self._symbol))\
                # - self.prefix_suffix_len
        # else:
            # return math.floor(self.width)\
                # - self.prefix_suffix_len
    @property
    def body(self):
        s = self._symbol * self.n_body_units
        n_remaining_chars = self.body_len - len(s)
        if n_remaining_chars >= 0:
            s += self._symbol[0:n_remaining_chars]
        return s
    @body.setter
    def body(self, value): self.symbol = value
    @property
    def _symbol(self):
        if self.symbol == 'high': return '¯'
        if self.symbol == 'mid':  return '─'
        if self.symbol == 'low':  return '_'
        if self.symbol == 'dash':  return '-'
        if len(self.symbol): return self.symbol
        else: return '_'

    def high(self,): return self.__call__('high')
    def mid(self, ): return self.__call__('mid')
    def low(self, ): return self.__call__('low')

    @_args2attrs(symbol=default_symbol)
    def __call__(self, symbol):
        # self.split_init(self.symbol)
        if self.symbol[0] == '#':
            self.prefix = '#'
            self.symbol = self.symbol[1:]
        else:
            self.prefix = ''
        return super().__call__()

class _StringVar:
    @_args2attrs()
    def __init__(self, max_nof_lines = 3,
                 width = 80,
                 prefix = ''): pass
    def __call__(self, k, v, prefix='', prefix2=None):
        if prefix is None: self.prefix = prefix
        else: self.prefix = prefix
        if prefix2 is None:
            prefix2 = ' '*len(self.prefix) if self.prefix else self.prefix
        _k = k
        k = f'{k} = ' if k != '' else ''
        k_short = f'{k[:-1]}' if k else ''
        msg = ''
        v = str(v)
        if v.endswith('\n'): v = v[:-1]
        next_msg = f"{k}{v}\n" if k else f"{v}\n"
        if len(next_msg) >= self.width-len(self.prefix):
            next_msg = f"{k_short}\n{v}"if k else f"{v}\n"

        next_msg_split = next_msg.split('\n')
        too_many = {
            'lines':len(next_msg_split) > self.max_nof_lines,
            'chars':len(next_msg) > self.width + len(self.prefix),
        }

        if not any(too_many.values()):
            msg += self.prefix + next_msg
        else:
            regex = r'.{' + str(self.width-len(self.prefix)) + r'}|.*\n'
                # + r'|'
            findall = re.findall(regex, next_msg)
            findall = list(filter(lambda s: s != '\n', findall))
            longer_than_1_line = False
            for i, s in enumerate(findall):
                prefix = prefix2 if longer_than_1_line else self.prefix
                if i == self.max_nof_lines:
                    msg += prefix + f"#<<< {_k} clipped >>>\n"
                    break
                msg += prefix + s
                if msg[-1] != '\n': msg += '\n'
                longer_than_1_line = True
        # debug(str(findall) + '\n')
        # msg += f'prefix = {self.prefix}\n'
        # msg += f'prefix = {self.prefix}\n'
        return msg

_strvar = _StringVar()


class Source:
    def __init__(self):
        self.forward_bulletpoint = '--> '
        self.backward_bulletpoint = ' <--'
    @property
    def class_firstline(self):
        # log(self.line)
        # log(self.funcbody_upto_line)
        return self.classbody_upto_line.split('\n')[0] + '\n'
    @property
    def func_firstline(self):
        return self.funcbody_upto_line.split('\n')[0] + '\n'
    # @property
    # def rel_lineno(self):
        # return self.lineno - self.func_firstlineno

class SourceInsideObj(Source):
    @property
    def classbody_upto_line(self):
        return inspect.getsource(self.obj)[self.class_firstlineno:self.lineno]
    @property
    def funcbody(self):
        return inspect.getsource(self.func)
    @property
    def funcbody_upto_line(self):
        return self.funcbody[self.func_firstlineno:self.lineno]
    @property
    def line(self): pass

# class SourceOutsideObj(SourceLine):
class SourceFromFilenameAndLineno(Source):
    def __init__(self, filename=None, lineno=None):
        if filename: self.filename = filename
        if lineno: self.lineno = lineno
        super().__init__()
        # self.add_bulletpoint_to_line()
    @property
    def at_deepest_user_trace(self): return True
    @property
    def filebody(self,):
        with open(self.filename) as f: self._filebody = list(f)
        self.add_bulletpoint_to_line()
        return self._filebody

    def add_bulletpoint_to_line(self,):
        lineno = self.lineno - 1
        try: len(self._filebody)
        except: return
        try: len(self._filebody[0])
        except: return
        # debug(self.filename, self.lineno, len(self.filebody))
        if len(self._filebody[lineno]) < 4: return
        if self._filebody[lineno][0:4] != '    ':
            self._filebody[lineno] = self._filebody[lineno][:-1]\
                + self.backward_bulletpoint + '\n'
        else:
            self._filebody[lineno] = self.forward_bulletpoint\
                + self._filebody[lineno][4:]

    def sourcefrom_regex_to_lineno(self, regex, start_lineno=0,
                                   upto_lineno=None):
        if upto_lineno is None: upto_lineno = self.lineno - 1
        # upto_lineno = upto_lineno - 1
        # return ''.join(self.filebody[start_lineno:upto_lineno+1])
        ret_start_lineno = upto_lineno
        for s in reversed(self.filebody[start_lineno:upto_lineno+1]):
            # print(s)
            if re.search(regex, s): break
            ret_start_lineno -= 1
        code = ''.join(self.filebody[ret_start_lineno:upto_lineno])\
            if ret_start_lineno >= 0 else ''
        return code

    def sourcefrom_lineno_to_regex(self, regex, start_lineno=0,
                                   upto_lineno=None):
        if upto_lineno is None: upto_lineno = len(self.filebody)
        if upto_lineno is None: upto_lineno = self.lineno - 1
        # upto_lineno = upto_lineno - 1
        # return ''.join(self.filebody[start_lineno:upto_lineno+1])
        ret_upto_lineno = start_lineno
        for s in self.filebody[start_lineno:upto_lineno+1]:
            # print(s)
            if re.search(regex, s): break
            ret_upto_lineno -= 1
        code = ''.join(self.filebody[start_lineno:ret_upto_lineno])\
            if ret_upto_lineno >= 0 else ''
        return code

    @property
    def classbody_upto_line(self):
        return self.sourcefrom_regex_to_lineno(r'^class.*:$')
    @property
    def funcbody_upto_line(self):
        return self.sourcefrom_regex_to_lineno(r'\bdef.*:$')
    @property
    def line(self):
        # self.add_bulletpoint_to_line()
        return self.filebody[self.lineno-1]
    @property
    def funcbody_after_line(self):
        return self.sourcefrom_lineno_to_regex(
            r'\bdef.*:$',
            start_lineno=self.lineno,
            upto_lineno=len(self.filebody)
        )

class SourceFromException(SourceFromFilenameAndLineno):
    def __init__(self, exc):
        self.exc = exc
        super().__init__()
    @property
    def filename(self): return self.exc.filename
    @property
    def lineno(self): return self.exc.lineno
    # @property
    # def func_firstlineno(self): pass # TODO

class SourceFromTraceback(SourceFromFilenameAndLineno):
# class SourceFromTraceback(SourceInsideObj):
    def __init__(self, tb):
        self.tb = tb
        self.tb_head = tb
        super().__init__()
    def __iter__(self, ):
        self.started_iter = False
        return self
    def __next__(self, ):
        if self.started_iter is False:
            self.tb = self.tb_head
            self.started_iter = True
            return self
        elif  self.tb.tb_next:
            self.tb = self.tb.tb_next
            return self
        else:
            self.started_iter = False
            raise StopIteration
        # return self.tb if self.tb else raise StopIteration

    @property
    def at_deepest_trace(self):
        return self.tb.tb_next == None
    @property
    def at_deepest_user_trace(self):
        if self.at_deepest_trace: return True
        else:
            next = SourceFromTraceback(self.tb.tb_next)
            return re.search('/anaconda', next.filename)
    @property
    def frame(self): return self.tb.tb_frame
    @property
    def globals(self): return self.frame.f_globals
    @property
    def locals(self): return self.frame.f_locals
    @property
    def filename(self): return self.globals['__file__']
    @property
    def lineno(self): return self.tb.tb_lineno

    # @property
    # def code(self): return self.frame.f_code
    # @property
    # def func_firstlineno(self): return self.code.co_firstlineno
    # @property
    # def func_name(self): return self.code.co_name
    @property
    def obj(self): return self.locals.pop('self', None)
    # @property
    # def func(self):
        # try: return getattr(self.obj, self.func_name)
        # except: return None

    # @property
    # def sig(self): return inspect.signature(self._func)
    # @property
    # def params(self): return self.sig.parameters
    # @property
    # def func_arg_values(self):
        # msg = ''
        # for name in self.params:
            # msg += f'{name} = {self.locals.pop(name, "Error")}\n'
        # return msg


_header = _Header()
def bar(symbol): print(_header(symbol))
def sbar(symbol): return _header(symbol) + '\n'
def section(title):
    bar('low')
    print('#' + ' '*28 + '-*- ' + title + '  -*-')
    bar('high')
def s_section(title):
    msg = ''
    msg += sbar('low')
    msg += '#' + ' '*28 + '-*- ' + title + '  -*-\n'
    msg += sbar('high')
    return msg

class DebuggerMessage:
    def __call__(self, msg,):
        if self.logger:
            self.logger(msg, end='')
            return None
        else: return msg

class ExceptionMessage(DebuggerMessage):
    def __init__(self, exc=None):
        self.exc = exc
    def __call__(self, exc=None, logger=print):
        if(exc): self.exc = exc
        self.logger = logger
        msg = ''
        msg += '\n'
        # msg += log.sbar('mid')
        msg += self.msg
        msg += sbar('low')
        # msg += '# '
        msg += self.type
        msg += sbar('high')
        return super().__call__(msg)
    @property
    def msg(self): return str(self.exc) + '\n'
    @property
    def type(self): return '' + self.exc.__class__.__name__ + '\n'

class SourceMessage(DebuggerMessage):
    def __init__(self, src=None):
        self.src = src
        self.max_nof_locals = 20
    def __call__(self, src=None, logger=print):
        if(src): self.src = src
        self.logger  = logger
        msg = ''
        msg += sbar('low')
        msg += self.src_text
        return super().__call__(msg)

    def with_traceback(self, tb):
        self.src = tb
        return self
    @property
    def infolevel(self):
        if not self.in_user_code:
            infolevel = 'none'
        elif self.src.at_deepest_user_trace:
            infolevel = 'high'
        else:
            infolevel = 'low'
        return infolevel
    @property
    def src_text(self):
        msg = ''
        if self.infolevel == 'none':
            msg += self.fileinfo
            pass
        if self.infolevel == 'low':
            msg += self.fileinfo
            # msg += '\n'
            msg += self.src.class_firstline
            msg += self.src.func_firstline
            msg += self.src.line
        elif self.infolevel == 'high':
            msg += self.fileinfo
            msg += '\n'
            msg += self.src.class_firstline
            msg += self.src.funcbody_upto_line
            # msg += self.src.funcbody
            msg += self.src.line
            # msg += self.locals
        # msg += self.src.funcbody_after_line
        return msg
    @property
    def locals(self):
        msg = ''
        locals = self.src.locals
        for i, (k, v) in enumerate(locals.items()):
            if i >= self.max_nof_locals:
                msg += '#       >>> Remaning locals clipped <<<\n'
                break
            if k == 'self':
                continue
                # msg += '\n'
            msg += _strvar(k, v)
        return msg
    @property
    def fileinfo(self):
        msg = ''
        msg += f'  File "{self.src.filename}", line {self.src.lineno}\n'
        if not self.in_user_code: msg = '# ' + msg
        return msg
    @property
    def in_user_code(self):
        return not re.search('/anaconda', self.src.filename)


class Debugger:
    def excepthook(self, exc_type=None, exc_obj=None, tb=None):
        tb_head_src = SourceFromTraceback(tb)
        src_msg = SourceMessage()

        # deepest_user_tb = tb_head_src.tb
        for tb_src in tb_head_src:
            if tb_src.at_deepest_user_trace:
                deepest_user_tb = tb_src
            src_msg(tb_src)

        # exc_src = SourceFromTraceback(exc_obj.with_traceback(
            # tb_src.tb).__traceback__)
        # exc_src = SourceFromTraceback(exc_obj.__traceback__)
        locals_en = True
        if hasattr(exc_obj, 'lineno'):
            exc_src = SourceFromFilenameAndLineno(
                exc_obj.filename, exc_obj.lineno)
            src_msg(exc_src)
            locals_en = False

        exc_msg = ExceptionMessage(exc_obj)
        exc_msg()
        if locals_en:
            print(src_msg.with_traceback(deepest_user_tb).locals)

    def __init__(self, backup_debugger=None):
        self.backup_debugger = backup_debugger
        sys.excepthook = self.__call__
        self.header = _Header()
        # sys.settrace(self.tracer)
        # sys.setprofile(self.tracer)
    def tracer(self, frame, event, arg):
        return self.tracer

    def use_builtin_debugger(self): # for real debugger
        print()
        section('Built-in Debugger (from Debugger2) >>>')
        print()
        traceback.print_exc(file=sys.stdout)
        section('<<< Built-in Debugger (from Debugger2)')

    def __call__(self, exc_type=None, exc_obj=None, tb=None):
        section('Debugger2 >>>')
        try:
            # intentional_test_error_in_debugger2
            self.excepthook(exc_type, exc_obj, tb)
            section('<<< Debugger2')
        except:
            print('Debugger2 Failed, calling backup_debugger\n')
            if self.backup_debugger:
                exc_type, exc_obj, tb = sys.exc_info()
                self.backup_debugger(exc_type, exc_obj, tb)
                section('xxx Debugger2')
            else:
                # section('xxx Debugger2')
                print('Backup_Debugger Failed, calling Built-in debugger\n')
                self.use_builtin_debugger()
# debugger = Debugger()
