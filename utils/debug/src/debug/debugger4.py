import re
# from .log import log
import sys
# import inspect
import traceback
import unittest
from copy import deepcopy

from utils.args2attrs import args2attrs
from utils.utils import Utils as ut
from varname.helpers import debug

# from .log0 import log0 as log
from . import Header
from . import Log
from . import dlog
from . import log
from . import strvar
from .trace import *

header = Header()


class DebuggerMessage:
    def __call__(self, msg,):
        if self.log:
            self.log(msg, end='')
            return None
        else:
            return msg


class ExceptionMessage(DebuggerMessage):
    def __init__(self, exc=None):
        self.exc = exc

    def __call__(self, exc=None, log=print):
        if(exc):
            self.exc = exc
        dlog.header('low')
        dlog(self.type)
        dlog.header('high')
        dlog.raw(self.msg)
        dlog.ln()
        dlog.header('#-')

    @property
    def msg(self):
        msg = ':\n'.join(str(self.exc).split(': ')) + '\n'
        msg = re.sub("'", '', msg)
        return msg

    @property
    def type(self): return '' + self.exc.__class__.__name__ + '\n'


class SourceMessage(DebuggerMessage):
    @args2attrs()
    def __init__(self, src=None, log=dlog, max_nof_locals=20): pass

    def __call__(self, src=None, log=print):
        if(src):
            self.src = src
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
            infolevel = 'high'
            # infolevel = 'low'
        return infolevel

    @property
    def src_text(self):
        if self.infolevel == 'none':
            # dlog(self.fileinfo)
            pass
        if self.infolevel == 'low':
            dlog.header('low')
            dlog(self.fileinfo)
            dlog(self.src.class_firstline)
            dlog(self.src.func_firstline)
            dlog(self.src.line)
            # dlog(self.src.funcbody_after_line)
        elif self.infolevel == 'high':
            dlog.header('low')
            dlog(self.fileinfo)
            dlog.ln()
            dlog(self.src.class_firstline)
            dlog.raw(self.src.funcbody_upto_line)
            dlog(self.src.line)
            dlog(self.src.funcbody_after_line)
            dlog.ln()

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

    # @snoop
    def getattr_ifhas(self, attrname, objref, objname):
        default = f"# <{objname}.{attrname} founnot found>"
        if objref is None:
            # log('getting from locals:', objref, objname, attrname)
            attrvalue = self.src.locals.get(attrname, default)
            if attrvalue == default:
                attrvalue = self.src.globals.get(attrname, default)
        else:
            # log('popping attr:', objref, objname, attrname)
            attrvalue = ut.getattr_ifhas(objref, attrname, default)
        if attrvalue == default:
            gotattr = False
        else:
            gotattr = True
        # log('after:',  objref, objname, attrvalue, gotattr)
        return attrvalue, gotattr

    @property
    # @snoop
    def call_locals(self):
        vars = self.src.line_func_call_attrs
        # log(vars)
        gotattr = True
        for i, full_names in enumerate(vars):
            # log(f'\nfull_names {i}: {full_names}')
            cycle_names = full_names.split('.')
            objref = objname = None
            while cycle_names:
                attrname = cycle_names[0]
                cycle_names = '.'.join(cycle_names).split('.')[1:]
                # log('\niteration before:', cycle_names, objref, objname,
                # attrname)
                attrvalue, gotattr = self.getattr_ifhas(
                    attrname, objref, objname)
                objref = attrvalue
                objname = attrname
                # log('iteration after:', cycle_names, objref, objname, attrvalue)
            if i >= self.max_nof_locals:
                dlog('       # <<< Remaning locals clipped >>>\n')
                break
            if gotattr is False:
                full_names = '# ' + full_names
            else:
                dlog(strvar(full_names, attrvalue), prefix='')

    @property
    def fileinfo(self):
        msg = f'  File "{self.src.filename}", line {self.src.lineno}'
        if not self.in_user_code:
            msg = '# ' + msg
        return msg

    @property
    def in_user_code(self):
        return not re.search('/python', self.src.filename)


class Debugger(unittest.TestResult):
    def __init__(self, *args, backup_debugger=None, **kwds):
        self.backup_debugger = backup_debugger
        sys.excepthook = self.__call__
        self.header = Header()
        super().__init__(*args, **kwds)
        self.error = False
        # sys.settrace(self.tracer)
        # sys.setprofile(self.tracer)

    def __call__(self, exc_type=None, exc_obj=None, tb=None):
        dlog.section('Debugger4 >>>')
        try:
            # intentional_test_error_in_debugger4
            self.excepthook(exc_type, exc_obj, tb)
            dlog.section('<<< Debugger4')
        except:
            print('Debugger4 Failed, calling backup_debugger\n')
            if self.backup_debugger:
                exc_type, exc_obj, tb = sys.exc_info()
                self.backup_debugger(exc_type, exc_obj, tb)
                dlog.section('xxx Debugger4')
            else:
                # dlog.section('xxx Debugger4')
                print('Backup_Debugger Failed, calling Built-in debugger\n')
                self.use_builtin_debugger()

    def excepthook(self, exc_type=None, exc_obj=None, tb=None):
        tb_head_src = SourceFromTraceback(tb)
        src_msg = SourceMessage()

        # deepest_user_tb = tb_head_src.tb
        count = 0
        shallowest_lib_tb = None
        for tb_src in tb_head_src:
            src_msg(tb_src)
            count += 1
            if count > 100:
                dlog('>>> Recursion Detected, Breaking')
                break

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
        try:
            src_msg.with_traceback(tb_src.deepest_user_src).call_locals
        except:
            pass
        # elif locals_en:
        dlog.header('#-')
        try:
            src_msg.with_traceback(tb_src.deepest_user_src).locals
        except:
            pass

    def tracer(self, frame, event, arg):
        return self.tracer

    def use_builtin_debugger(self):  # for real debugger
        print()
        dlog.section('Built-in Debugger (from Debugger4) >>>')
        print()
        traceback.print_exc(file=sys.stdout)
        dlog.section('<<< Built-in Debugger (from Debugger4)')

    def pushError(self, err):
        if not self.error:
            # log(err)
            self(*err)
            # self(sys.last_type, sys.last_value, sys.last_traceback)
        self.error = True

    def addFailure(self, test, err):
        # here you can do what you want to do when a test case fails
        # log('test failed!')
        super().addFailure(test, err)
        self.pushError(err)

    def addError(self, test, err):
        # here you can do what you want to do when a test case raises an error
        # log('debugger4: test case error!')
        super().addError(test, err)
        self.pushError(err)

    @property
    def testrunner(self,):
        return unittest.TextTestRunner(resultclass=self.__class__)
