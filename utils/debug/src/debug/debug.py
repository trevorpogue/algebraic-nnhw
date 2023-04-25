import cProfile
import runpy
import sys
import unittest
from contextlib import redirect_stdout

import pytest

import debug
from debug import dlog
from debug import log


class Debug():
    # def __call__(self, module, *args) -> None:
    def __call__(self, *args) -> None:
        # args = list(filter(None, args))
        debugger = debug.debugger()
        self.debugger = debugger
        from experiment import do_experiment
        sys.argv = sys.argv[1:]
        module = sys.argv[0]
        if do_experiment:
            module = 'experiment'
            module_arg_i = 1
            zero = 0
            sys.argv = sys.argv[zero:module_arg_i]
        if module == 'unittest':
            self.unittest(*sys.argv[1:])
        if module == 'pytest':
            sys.argv = sys.argv[1:]
            file = '*scraplog*'
            file = log.file
            with open(file, 'a') as f:
                with redirect_stdout(f):
                    """"""
            prof_en = False
            # prof_en = True
            if prof_en:
                import cProfile
                import io
                import pstats
                from pstats import SortKey
                pr = cProfile.Profile()
                pr.enable()
            # ... do something ...
            pytest.main(sys.argv)
            # ... did something ...
            if prof_en:
                pr.disable()
                s = io.StringIO()
                sortby = SortKey.CUMULATIVE
                sortby = SortKey.TIME
                ps = pstats.Stats(pr, stream=s).strip_dirs(
                ).sort_stats(sortby).reverse_order()
                ps.print_stats()
                log.raw(s.getvalue())
            # if hasattr(sys, 'last_traceback'):
                # debugger(sys.last_type, sys.last_value, sys.last_traceback)
        else:
            runpy.run_module(module, run_name='__main__', alter_sys=True)

    def unittest(self, path, pattern='test*.py', top_level_dir=None):
        if top_level_dir is None:
            top_level_dir = path
            # sys.argv = sys.argv[1:]
            # sys.argv[0] = 'unittest'
            # runpy.run_path(path)
            # return
            testrunner = self.debugger.testrunner
            # log(path, pattern, top_level_dir)
            log(path, pattern, top_level_dir)
            suite = unittest.TestLoader().discover(path,
                                                   pattern=pattern,
                                                   top_level_dir=top_level_dir,
                                                   )
            testrunner.run(suite)
