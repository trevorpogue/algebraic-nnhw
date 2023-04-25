# from ..utils.args2attrs import args2attrs
__all__ = ['SourceFromFilenameAndLineno', 'SourceFromTraceback']
import inspect
import re
# from src.debug.logger import log
from varname.helpers import debug

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
    @property
    def line_func_call_attrs(self):
        prev_lines = self.filebody[self.lineno-3: self.lineno-1]
        prev_lines = '\n'.join(prev_lines)
        line = prev_lines + self.line + self.funcbody_after_line
        # line = self.line + self.funcbody_after_line
        # log(line)
        ret1 = re.findall(r'[\(, ]([\w\.]*)[\),]', line)
        ret2 = re.findall(r'self\.[\w\.]*', line)
        ret = re.findall(r'(\b[a-zA-Z][\w\.]*)\b', line)
        # ret = re.findall(r'(\b[a-zA-Z][\w\.])*\b', line)
        ret = list(filter(lambda s: s != '', ret))
        ret = dict.fromkeys(ret)
        ret.pop('return', None)
        # ret1 = dict.fromkeys(ret1)
        # ret2 = dict.fromkeys(ret2)
        # ret = {**ret2, **ret1}
        # ret = ''.join(ret).split(',')
        return list(ret.keys())
        # return ret


class SourceInsideObj(Source):
    @property
    def classbody_upto_line(self):
        return inspect.getsource(self.obj)[self.class_firstlineno:self.lineno]

    @property
    def funcbody(self): return inspect.getsource(self.func)

    @property
    def funcbody_upto_line(self):
        return self.funcbody[self.func_firstlineno:self.lineno]
    # @property
    # def line(self): pass


# class SourceOutsideObj(SourceLine):
class SourceFromFilenameAndLineno(Source):
    def __init__(self, filename=None, lineno=None):
        if filename:
            self.filename = filename
        if lineno:
            self.lineno = lineno
        super().__init__()
        # self.add_bulletpoint_to_line()

    @property
    def at_deepest_user_trace(self): return True

    @property
    def filebody(self,):
        with open(self.filename) as f:
            self._filebody = list(f)
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
        return self.sourcefrom_regex_to_lineno(r'^class \w+.*$')
    @property
    def funcbody_upto_line(self):
        return self.sourcefrom_regex_to_lineno(r'\bdef \w+\(.*$')
    @property
    def line(self):
        return self.filebody[self.lineno-1]
    @property
    def funcbody_after_line(self):
        if len(self.filebody) > self.lineno:
            return (
                re.sub('\n\n', '\n',
                          '\n'.join(
                self.filebody[self.lineno:self.lineno + 3]))
        )
        else:
            return ''
        # return self.sourcefrom_lineno_to_regex(
            # r'\bdef.*:$',
            # start_lineno=self.lineno,
            # upto_lineno=len(self.filebody)
        # )

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
        # self.deepest_user_src = None
        # self.shallowest_lib_src = None
        super().__init__()
    def __iter__(self, ):
        self.started_iter = False
        return self
    def __next__(self, ):
        if self.started_iter is False:
            self.tb = self.tb_head
            self.deepest_user_src = self.__class__(self.tb)
            self.started_iter = True
            return self
        elif  self.tb.tb_next:
            self.tb = self.tb.tb_next
            if self.in_user_trace:
                self.deepest_user_src = self.__class__(self.tb)
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
        in_user_trace = not re.search('/python', self.filename)
        if not in_user_trace: return False
        if self.at_deepest_trace and in_user_trace: return True
        else:
            next = SourceFromTraceback(self.tb.tb_next)
            return re.search('/python', next.filename)
    @property
    def in_user_trace(self):
            return not re.search('/python', self.filename)
    @property
    def frame(self): return self.tb.tb_frame
    @property
    def globals(self): return self.frame.f_globals
    @property
    def locals(self):
        # if self.at_deepest_user_trace:
        return self.frame.f_locals
        # else:
            # return self.params
    @property
    def filename(self): return self.globals['__file__']
    @property
    def lineno(self): return self.tb.tb_lineno

    @property
    def code(self): return self.frame.f_code
    # @property
    # def func_firstlineno(self): return self.code.co_firstlineno
    @property
    def func_name(self): return self.code.co_name
    @property
    def obj(self): return self.locals.pop('self', None)
    @property
    def func(self):
        try: return getattr(self.obj, self.func_name)
        except: return None
    @property
    def sig(self): return inspect.signature(self.func)
    @property
    def params(self): return self.sig.parameters
    # @property
    # def func_arg_values(self):
        # msg = ''
        # for name in self.params:
            # msg += f'{name} = {self.locals.pop(name, "Error")}\n'
        # return msg
