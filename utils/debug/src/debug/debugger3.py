__all__ = ['Debugger']
from .trace import SourceFromFilenameAndLineno, SourceFromTraceback
from copy import deepcopy
# from .log import log
import sys
# import inspect
import traceback
import re
from varname.helpers import debug
from varname import argname
from varname.helpers import debug
from utils.redict import ReDict
import inspect
from inspect import signature
from itertools import repeat
from .trace import *
from utils.args2attrs import args2attrs
import re
import copy
import math


class Message():
    # _verbose_init_keys=('prefix', 'body', 'suffix', )
    # _verbose_init_keys={'prefix':'', 'body':'', 'suffix':'', }
    _verbose_init_keys = dict(prefix='', body='', suffix='', )
    @args2attrs(**_verbose_init_keys)
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

    # @args2attrs()
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


class Header(Message):
    default_symbol = '_'

    @args2attrs('width')
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
        else: return self.default_symbol

    def high(self,): return self.__call__('high')
    def mid(self, ): return self.__call__('mid')
    def low(self, ): return self.__call__('low')

    @args2attrs(symbol=default_symbol)
    def __call__(self, symbol):
        # self.split_init(self.symbol)
        if self.symbol[0] == '#':
            self.prefix = '#'
            self.symbol = self.symbol[1:]
        else:
            self.prefix = ''
        return super().__call__()


class StringVar:
    @args2attrs()
    def __init__(self, max_nof_lines = 3,
                 width = 80,
                 prefix = ''): pass
    @args2attrs()
    def __call__(self, k, v, prefix='', prefix2=None, keep_blank_line=False):
        if prefix2 is None:
            prefix2 = ' '*len(self.prefix) if self.prefix else self.prefix
        if keep_blank_line and v == '\n': return '\n\n'
        k = str(k)
        v = str(v)
        _k = k
        k = f'{k} = ' if k != '' else ''
        k_short = f'{k[:-1]}' if k else ''
        if v == '': k = k_short
        msg = ''
        while v.endswith('\n'): v = v[:-1]
        next_msg = f"{k}{v}\n" if k else f"{v}\n"
        if len(next_msg) >= self.width-len(self.prefix):
            next_msg = f"{k_short}\n{v}\n"if k else f"{v}\n"

        next_msg_split = next_msg.split('\n')
        too_many = {
            'lines':len(next_msg_split) > self.max_nof_lines,
            'chars':len(next_msg) > (self.width - len(self.prefix)),
        }

        next_msg = re.sub("n't ", "nt ", next_msg)
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
                if i == self.max_nof_lines and i < len(findall) - 1:
                    msg += prefix + f"# <<< {_k} clipped >>>\n"
                    msg += findall[-1]
                    break
                msg += prefix + s
                longer_than_1_line = True
        # debug(str(findall) + '\n')
        # msg += f'prefix = {self.prefix}\n'
        # msg += f'prefix = {self.prefix}\n'
        while msg and msg[-1] == '\n': msg = msg[:-1]
        if keep_blank_line or (msg != ''): msg += '\n'
        return msg

strvar = StringVar()


class Log():
    # @args2attrs()
    # def __init__(self, prefix='', 'body', suffix=''):
    default_prefix = '>       '
    @args2attrs()
    def __init__(self, *args,
                 done_first_print = False,
                 caller_class  = Message(
                     f'\n,,:'),
                 caller_method = Message('    ,,:', suffix=''),
                 # prefix = '>       ',
                 prefix = '',
                 # default_prefix = '',
                 file = '*outlog*',
                 str_prefix = None,
                 var_prefix = None,
                 value_only = False,
                 log_method_name = None,
                 banner_en=True,
                 class_ens = {},
                 en = None,
                 default_suffix = '',
                 **kwds
    ):
        # super().__init__(*args, **kwds)
        self.sheader = Header()
        self.class_ens = ReDict(self.class_ens)
        if self.str_prefix is None: self.str_prefix = self.prefix
        if self.var_prefix is None: self.var_prefix = self.prefix
        pass

        self.str_suffix = ''
        self.var_suffix = ''
        self.var_suffix = ''
        self.done_firstwrite = False

    def rm(self, ):
        import os
        try: os.remove('/home/trevor/dla/python/' + self.file)
        except: pass

    def header(self, symbol): self(self.sheader(symbol))

    def bar(self, symbol):
        # self.__call__(self.header(symbol), prefix='', suffix='')
        self(self.header(symbol))

    def sbar(self, symbol):
        return self.sheader(symbol) + '\n'

    def section(self, title):
        self.header('low')
        self('#' + ' '*28 + '-*- ' + title + '  -*-')
        self.header('high')

    def s_section(self, title):
        msg = ''
        msg += self.sbar('low')
        msg += '#' + ' '*28 + '-*- ' + title + '  -*-\n'
        msg += self.sbar('high')
        return msg

    def ln(self, n=1):
        self.raw('\n'*n)

    def p(self, ):
        print(s)

    def process_caller_locals(self, default_logen=None):
        if default_logen: self.log_en = default_logen
        caller_locals = self.caller_frame.f_locals
        caller_local_logen = caller_locals.pop('log_en', self.log_en)

        self.src = SourceFromFilenameAndLineno(
            self.caller_frame.f_globals['__file__'], self.caller_frame.f_lineno)
        caller_method = self.src.func_firstline
        caller_classname = self.src.class_firstline

        # choose when to log
        self.log_en = True
        if caller_local_logen is not None: self.log_en = caller_local_logen
        if self.class_ens.pop_reverse(caller_classname, None) is not None:
            self.log_en = self.class_ens.pop_reverse(caller_classname, None)
        if self.en != None: self.log_en = self.en
        #
        self.log_method_name = caller_method != self.caller_method
        self.log_class_name = caller_classname != self.caller_class.name
        self.caller_method.name = self.src.func_firstline
        self.caller_class.name = caller_classname

    def raw(self, s):
        if self.file:
            # with open(self.file, 'a' if self.done_firstwrite else 'w') as f:
            with open(self.file, 'a') as f:
                f.write(s)
                self.done_firstwrite = True
        else: print(s, end='')
            # f.writelines(L)

    def do_printing(self):
        """do actual logging/printing"""
        if not self.log_en: return ''
        if self.banner_en:
            if not self.done_first_print:
            # if re.search('Debugger', self.caller_class.name):
                self.done_first_print = True
                self.raw(self.s_section('Log'))
            if self.log_class_name:
                self.raw(self.sheader('_') + '\n')
                self.raw(self.src.class_firstline)
            if self.log_method_name:
                self.raw(self.sheader('#_') + '\n')
                self.raw(self.src.func_firstline)
                # msg += self.src.funcbody_upto_line
                self.raw(self.sheader('#-') + '\n')
                # msg += self.s_section('Log')
        if self.merge:
            self.raw(f"{', '.join(self.name_and_values)}"\
                + "{self.suffix}")
        else:
            for self.name_and_value in self.name_and_values:
                self.raw(self.name_and_value)
        # msg += '\n'

    # @args2attrs('merge', var='', prefix='', suffix='') # TODO
    def __call__(self, var,
                 *more_vars,
                 # more_vars=None,
                 prefix: str = None,
                 suffix: str = None,
                 merge: bool = False,
                 repr: bool = False, # pylint: disable=redefined-builtin
                 log_en = True,
                 keep_blank_line = False,
                 vars_only: bool = False) -> None:
        """Print variable names and values."""

        self.merge = merge
        var_names = argname(
            var, *more_vars,
            pos_only=True,
            vars_only=vars_only,
            func=self.__call__
        )
        if not isinstance(var_names, tuple):
            var_names = (var_names, )

        values = (var, *more_vars)
        self.name_and_values = []
        for var_name, value in zip(var_names, values):
            if self.value_only or (
            isinstance(var, str)\
               and (var_name[0] == "'")\
               or len(var_name) > 1 and (var_name[1] == "'")):
                # logging a user-entered string
                s = var
                # if var == '':
                if prefix is None: prefix = self.str_prefix
                if suffix is None: suffix = self.str_suffix
                s = strvar('', value, prefix=prefix,
                           keep_blank_line=keep_blank_line)
                # self.prefix = ''
                # self.suffix = self.str_suffix
            elif repr:
                if  prefix is None: prefix = self.var_prefix
                if suffix is None: suffix = self.var_suffix
                value = f"{value!r}"
                s = strvar(var_name, value, prefix=prefix)
            else:
                # s = f"\`{var_name}\`=\`{value}\`"
                # if isinstance(value, str): value = f"'{value}'"
                # s = f"{var_name} = `{value}`"
                if prefix is None: prefix = self.var_prefix
                if suffix is None: suffix = self.var_suffix
                s = strvar(var_name, value, prefix=prefix)
                # self.prefix = ''
            self.name_and_values.append(s)

        frame = inspect.currentframe()
        self.caller_frame = frame.f_back
        self.process_caller_locals(log_en)
        del frame
        del self.caller_frame
        self.do_printing()

# @property
# def frame(self, ):

# @property
# def caller_func_name(self, ):

# @property
# def caller_func_name(self, ):

def logargs(self, log=print, ):
    frame = currentframe()
    caller_locals = frame.f_back.f_locals
    caller_self = caller_locals['self']
    caller_func_name = getframeinfo(frame.f_back).function
    caller_method = getattr(caller_self, caller_func_name)

    try: ismethod = inspect.ismethod(getattr(caller_self, method.__name__))
    except: ismethod = False

    if not ismethod:
        raise ValueError("Use the decorator version of this function instead. "
                         "This function is currently "
                         "only supported for use in methods, not in functions")

    params = signature(method).parameters
    self_name = next(iter(params))
    log(f'{method.__name__}:')
    for name in params:
        value = caller_locals[name]
        log(f'ARG: {name}={value}')

    try: pass
    except: pass
    finally: del frame


dlog = Log(file=None, banner_en=False,
           prefix='',
           class_ens={},
           value_only=True)

log = Log()
log.en = False
log.class_ens = ReDict({
    'Counter': False,
    # 'ATilerTest':True,,
    # 'Tiler':False,
    'Space': False,
    'Tiler': True,
    # 'Debugger': False,
})


def _update_if_present(d2update, d2pass, name, d2check=None):
    if d2check is None: d2check = d2pass
    try:
        dummy = d2check[name]
        d2update[name] = d2pass[name]
        ret = True
    except: ret = False
    return ret


def args2attrs(*dec_names, **dec_bindings):
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
                _update_if_present(attr_bindings, dec_bindings, name)
                _update_if_present(attr_bindings, bindings2pass, name)

            for name in attr_bindings:
                # debug(name)
                # debug(attr_bindings[name])
                setattr(self, name, attr_bindings[name])
                # debug(getattr(self, name))
                # except: pass
            return method(self, **bindings2pass)

        return wrapper
    return decorator

def getattr_ifhas(cls, objref, attrname, default=None):
    if hasattr(objref, attrname):
        log('gotattr', objref, attrname)
        attrvalue = getattr(objref, attrname)
    else:
        log('noattr', objref, attrname, default)
        attrvalue = default
    log(attrvalue)
    return attrvalue

header = Header()

class DebuggerMessage:
    def __call__(self, msg,):
        if self.log:
            self.log(msg, end='')
            return None
        else: return msg

class ExceptionMessage(DebuggerMessage):
    def __init__(self, exc=None):
        self.exc = exc
    def __call__(self, exc=None, log=print):
        if(exc): self.exc = exc
        dlog.header('low')
        dlog(self.type)
        dlog.header('high')
        dlog(self.msg)
        dlog.header('#-')
    @property
    def msg(self): return ':\n'.join(str(self.exc).split(': ')) + '\n'
    @property
    def type(self): return '' + self.exc.__class__.__name__ + '\n'

class SourceMessage(DebuggerMessage):
    @args2attrs()
    def __init__(self, src=None, log=dlog, max_nof_locals = 20): pass
    def __call__(self, src=None, log=print):
        if(src): self.src = src
        dlog.header('low')
        self.src_text

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
        if self.infolevel == 'none':
            dlog(self.fileinfo)
            pass
        if self.infolevel == 'low':
            dlog(self.fileinfo)
            dlog(self.src.class_firstline)
            dlog(self.src.func_firstline)
            dlog(self.src.line)
            # dlog(self.src.funcbody_after_line)
        elif self.infolevel == 'high':
            dlog(self.fileinfo)
            dlog(self.src.class_firstline)
            dlog.raw(self.src.funcbody_upto_line)
            dlog(self.src.line)
            dlog(self.src.funcbody_after_line)

    @property
    def locals(self):
        locals = self.src.locals
        vars = dict.fromkeys(self.src.line_func_call_attrs)
        for i, (k, v) in enumerate(locals.items()):
            if vars.get(k, '__notfound__') != '__notfound__':
                continue  # key was already printed in call_locals
            if i >= self.max_nof_locals:
                dlog('       # <<< Remaning locals clipped >>>\n')
                break
            if k == 'self':
                continue
            dlog(strvar(k, v),
                 # prefix='>       '
            )

    def getattr_ifhas(self, attrname, objref, objname):
        default = f"# <{objname}.{attrname} not found>"
        if objref is None:
            log('getting from locals:', objref, objname, attrname)
            attrvalue = self.src.locals.get(attrname, default)
            if attrvalue == default:
                attrvalue = self.src.globals.get(attrname, default)
        else:
            log('popping attr:', objref, objname, attrname)
            attrvalue = getattr_ifhas(objref, attrname, default)
        if attrvalue == default:
            gotattr = False
        else:
            gotattr = True
        log('after:',  objref, objname, attrvalue, gotattr)
        return attrvalue, gotattr

    @property
    def call_locals(self):
        vars = self.src.line_func_call_attrs
        log(vars)
        gotattr = True
        for i, full_names in enumerate(vars):
            log(f'\nfull_names {i}: {full_names}')
            cycle_names = full_names.split('.')
            objref = objname = None
            while cycle_names:
                attrname = cycle_names[0]
                cycle_names = '.'.join(cycle_names).split('.')[1:]
                log('\niteration before:', cycle_names, objref, objname,
                    attrname)
                attrvalue, gotattr = self.getattr_ifhas(
                    attrname, objref, objname)
                objref = attrvalue
                objname = attrname
                log('iteration after:', cycle_names, objref, objname, attrvalue)
            if i >= self.max_nof_locals:
                dlog('       # <<< Remaning locals clipped >>>\n')
                break
            if gotattr is False:
                full_names = '# ' + full_names
            dlog(strvar(full_names, attrvalue))

    @property
    def fileinfo(self):
        msg = f'  File "{self.src.filename}", line {self.src.lineno}'
        if not self.in_user_code: msg = '# ' + msg
        return msg
    @property
    def in_user_code(self):
        return not re.search('/anaconda', self.src.filename)

class Debugger:
    def __init__(self, backup_debugger=None):
        self.backup_debugger = backup_debugger
        sys.excepthook = self.__call__
        self.header = Header()
        # sys.settrace(self.tracer)
        # sys.setprofile(self.tracer)

    def __call__(self, exc_type=None, exc_obj=None, tb=None):
        dlog.section('Debugger3 >>>')
        try:
            # intentional_test_error_in_debugger3
            self.excepthook(exc_type, exc_obj, tb)
            dlog.section('<<< Debugger3')
        except:
            print('Debugger3 Failed, calling backup_debugger\n')
            if self.backup_debugger:
                exc_type, exc_obj, tb = sys.exc_info()
                self.backup_debugger(exc_type, exc_obj, tb)
                dlog.section('xxx Debugger3')
            else:
                # dlog.section('xxx Debugger3')
                print('Backup_Debugger Failed, calling Built-in debugger\n')
                self.use_builtin_debugger()

    def excepthook(self, exc_type=None, exc_obj=None, tb=None):
        tb_head_src = SourceFromTraceback(tb)
        src_msg = SourceMessage()

        # deepest_user_tb = tb_head_src.tb
        shallowest_lib_tb = None
        for tb_src in tb_head_src:
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
        # if deepest_user_tb:
        src_msg.with_traceback(tb_src.deepest_user_src).call_locals
        # elif locals_en:
        dlog.header('#-')
        src_msg.with_traceback(tb_src.deepest_user_src).locals

    def tracer(self, frame, event, arg):
        return self.tracer

    def use_builtin_debugger(self): # for real debugger
        print()
        dlog.section('Built-in Debugger (from Debugger3) >>>')
        print()
        traceback.print_exc(file=sys.stdout)
        dlog.section('<<< Built-in Debugger (from Debugger3)')
