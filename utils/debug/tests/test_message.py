# from common import *
import unittest
from typing import Any

from debug import Header
from debug import log


class MessageTest(unittest.TestCase):
    def test_main(self):
        len_ = 79
        self.message = Header()
        self.assert_eval({
            "self.message('-')": '-'*len_,
            "self.message('#-')": '#'+'-'*(len_ - 1),
            "self.message('--')": '-'*len_,
            "self.message('#--')": '#'+'-'*(len_ - 1),
            "self.message('high')": '¯'*len_,
            "self.message('mid')": '─'*len_,
            "self.message('low')": '_'*len_,
            "self.message('#high')": '#'+'¯'*(len_ - 1),
            "self.message('#mid')": '#'+'─'*(len_ - 1),
            "self.message('#low')": '#'+'_'*(len_ - 1),
        })

    def assert_eval(self, eval_vs_expected: dict) -> None:
        for code, expected_value in eval_vs_expected.items():
            test_value = eval(code)
            # log(test_value)
            info_msg = f"got       {code} =\n{test_value}\nexpected  "\
                f"{code} =\n{expected_value}"
            err_msg = "\nERROR:\n" + info_msg
            log(info_msg, prefix='')
            self.assertEqual(test_value, expected_value, err_msg)

#
# if __name__ == '__main__':
    # unittest.main()
