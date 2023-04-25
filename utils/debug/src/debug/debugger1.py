# from common import *
import sys
import inspect
import traceback
import re

class Debugger:
    def __init__(self, ):
        sys.excepthook = self.__call__
        # sys.settrace(self.tracer)
        # sys.setprofile(self.tracer)
        self.events = []
        self.frames = []
        self.args = []

    def __call__(self, e_type=None, e_obj=None, tb=None):
        print('_'*80)
        print('#' + ' '*28 + '-*- Debugger >>> -*-')
        print('¯'*80)
        # print('\n'*0)
        try:
            # intentional_test_error_in_Debugger
            self.excepthook(e_type, e_obj, tb)
            # print('Debugger Passed')
            print('_'*80)
            print('#' + ' '*28 + '-*- <<< Debugger -*-')
            print('¯'*80)
        except:
            # print(self.backup_debuger.args)
            print('Debugger Failed, calling Built-in debugger')
            self.real_debugger()

    def excepthook(self, e_type=None, e_obj=None, tb=None, Debugger_=None):
        # if Debugger_:
            # debugger = Debugger()
            # sys.excepthook = next_debugger

        # obj = None
        # obj = obj.cause_error_Debugger
        # t
        # print('\n'*2)
        # print('\n'*0)
        # print('\n'*0)
        frame_ = inspect.currentframe()
        frame  = frame_
        # first_msg = '' + '_'*80 + '\n'
        # first_msg = first_msg + '#' + first_msg[:-2] + '\n'
        first_msg = ''
        msg = first_msg
        next_msg = ''
        tb_ = tb
        frame_summary_list = traceback.extract_tb(tb)

        fs_iter = iter(frame_summary_list)
        fs = next(fs_iter)
        while tb_ or fs:
            header = '' + '_'*80 + '\n'
            user_code = ''
            file = ''
            if tb_: user_code += self.print_trace_info(tb_, fs)[:-1]
            if fs: file += self.print_file(fs)
            msg += header
            msg += file + '\n' if user_code else '# ' + file
            msg += user_code
            # if msg != first_msg:
            try: tb_ = tb_.tb_next
            except: tb_ = None
            try: fs = next(fs_iter)
            except: fs = None
            # if not tb_: break
        print(msg[:-1])
        try:

            msg = '─'*80 + '\n'
            msg += self.printcodefrom_file_and_lineno(
                e_obj.filename, e_obj.lineno, print_file=True)[:-2]
            print(msg)
        except:
            pass
            # e_type, e_obj, tb = sys.exc_info()
            # traceback.print_last(limit=1)
            # print('─'*80)
            # print(traceback.format_list(frame_summary_list))
            # traceback.print_tb(e_type, file=sys.stdout)
            # traceback.print_last()
            # traceback.print_exception(e_type, e_obj, tb, limit=1)
            # traceback.print_exc(file=sys.stdout)
            # print('\n'.join(traceback.format_exception(
                # e_type, e_obj, tb, limit=0)))

        print('\n#' + '-'*79)
        # print('\n#' + '¯'*79)
        self.print_e_type(e_type, e_obj, tb)
        # print('¯'*80)
        # self.real_debugger()
        # print('─'*80)
        # print('_'*80)

        # print('\n'*0)
        # print('¯'*80)

    def real_debugger(self): # for real debugger
        # print('\n\n#' + '>'*79)
        # print('')
        # print('#' + '-'*79)
        print()
        print('_'*80)
        print('#' + ' '*28 + '-*- Built-in Debugger  -*-')
        print('¯'*80)
        print()
        # print()
        # traceback.print_last()
        traceback.print_exc(file=sys.stdout)
        # print('#' + '-'*79)
        # print('#' + '>'*79)

    def printcodefrom_file_and_lineno(self, file_name, line_no, errorln=None,
                                      print_file=False):
        if not errorln: errorln = line_no
        file_str = f'  File "{file_name}", line {line_no}\n\n'\
            if print_file else ''
        errorln -= 1
        with open(file_name) as f:
            efile = list(f)
        if efile[errorln][0:4] != '    ':
            efile[errorln] = efile[errorln][:-1] + ' <--' + '\n'
            return file_str + efile[errorln] + '\n'
        else:
            efile[errorln] = '--> ' + efile[errorln][4:]

        errorln_str = efile[errorln]
        # errorln_str = ''
        lineno = line_no - 1
        # lineno = line_no - 2
        for s in reversed(efile[0:lineno+1]):
            if re.search(r'\bdef.*:$', s): break
            lineno -= 1
        func_str = ''.join(efile[lineno:line_no]) + '\n' if lineno >= 0\
            else errorln_str

        if lineno < 0: lineno = line_no - 1
        for s in reversed(efile[0:lineno+1]):
            if re.search(r'^class.*:$', s): break
            lineno -= 1
        class_str = efile[lineno] + '\n' if lineno >= 0 else ''
        # class_str = efile[lineno] if lineno >= 0 else ''
        msg = file_str + class_str + func_str
        msg = msg.split('\n')
        return '\n'.join(msg)

    def tracer(self, frame, event, arg):
        # if event == 'exception':
            # self.excepthook(*arg)
        # self.events.append(event)
        # self.frames.append(event)
        # self.args.append(event)
        return self.tracer

    def print_trace_info(self, tb, fs):
        frame_ = tb.tb_frame
        locals_ = frame_.f_locals
        globals_ = frame_.f_globals
        code_ = frame_.f_code
        file = globals_['__file__']
        lineno = tb.tb_lineno
        # if not re_type.search(locals_.pop('__file_', ''), '/dla/python/'):
        # if not re.search('/dla/python/', code_.co_filename): return ''
        if re.search('/anaconda', file): return ''
        msg = ''
        obj = locals_.pop('self', None)
        # if obj:
        if False:

        # try:
        # if 1:
            # msg += '***'
            # print(inspect.getsource((obj)).split('\n')[0])
            class_1st_line = inspect.getsource(obj).split('\n')[0]
            msg += f"{class_1st_line}\n"
        # except: pass
        # if obj:
            # print(obj)
            func = getattr(obj, code_.co_name)
            func_source_lines = inspect.getsourcelines(func)[0]
            errorln = -(code_.co_firstlineno - lineno)
            func_source_lines[errorln] = '--> ' + func_source_lines[errorln][4:]
            func_source = ''.join(func_source_lines)
            msg += '***'
            msg += f"{func_source}\n"

        # except:
        else:
            errorln = lineno
            msg += self.printcodefrom_file_and_lineno(file, lineno)

        return msg
        for name, value in locals_.items():
            if name == 'self': continue
            next_msg = Label('   >    ,,\n')
            next_msg.body = f"{name} = {value}"
            if isinstance(value, type(torch.tensor([]))):
                next_msg.body = f"{name} ="
                msg += next_msg.str
                next_msg.prefix = '        '
                for s in f'{value}'.split('\n'):
                    next_msg.body = s
                    if re.match(r' *\Z', s):
                        msg += next_msg.body + next_msg.suffix
                    else:
                        msg += next_msg.str
            # TODO dict will be fine for this
            # TODO: at least put name on new ln
            elif len(f'{next_msg}') > 80 and 0:
                next_msg.body = f"{name} ="
                msg += next_msg.str
                next_msg.prefix = '        '
                for s in f'{value}'.split(', '):
                    next_msg.body = s
                    if re.match(r' *\Z', s):
                        msg += next_msg.body + next_msg.suffix
                    else:
                        msg += next_msg.str
            else:
                msg += next_msg.str
            msg += '\n'
        #
        # msg += f"{[*locals_.keys()]}\n"
        return msg

    # def parse_trace_sourcecode():

    def print_file(self, fs):
        if fs == None: return ''
        trace_lns = traceback.format_list([fs])[0].split('\n')[0:1]
        trace_type_lns = list(filter(len, trace_lns))
        trace_ln = trace_lns[0:1] + [''] + trace_lns[1:] + ['']
        trace_ln = '' + '\n'.join(trace_ln)
        # emsg = re.sub(", in ", "", emsg)
        return trace_ln[:-1]

    def print_e_type(self, e_type, msg, tb):
        e_type = traceback.format_exception(e_type, msg, tb)[-1]
        e_type = e_type.split(': ')
        etype = '# (' + ': '.join(e_type[:-1]) + ')'
        emsg = ''
        # emsg += '#' + '-'*79 + '\n'
        bullet_point = '>>> '
        bullet_point = ''
        emsg += bullet_point
        emsg += e_type[-1]
        separator = ',\n' + bullet_point
        emsg = separator.join(emsg.split(', '))
        emsg = re.sub("n't ", "nt ", emsg)
        # e_type = [etype, emsg]
        # e_type = [emsg[:-1], etype]
        xtra = '#' + '_'*79
        e_type = [emsg[:-1], xtra, etype]
        # e_type = [emsg, xtra, etype]
        e_type = '\n'.join(e_type)
        # print(e_type[:-1])
        print(e_type)
        # print('¯'*80)
        # print('\n'*0)
