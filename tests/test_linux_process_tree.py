"""Offline checks for detached Linux descendant handling."""

from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

from adaptive_qa.browser_process import _signal_linux_process, _terminate_linux_tree


class LinuxProcessTreeTests(unittest.TestCase):
    def setUp(self):
        signals = patch("adaptive_qa.browser_process.signal", SimpleNamespace(SIGSTOP=19, SIGKILL=9))
        signals.start()
        self.addCleanup(signals.stop)

    @patch("adaptive_qa.browser_process.os.killpg", create=True)
    @patch("adaptive_qa.browser_process._signal_linux_process")
    @patch("adaptive_qa.browser_process._linux_descendants")
    def test_detached_descendants_are_stopped_before_group_termination(self, descendants, send, group):
        descendants.side_effect = [{101: "start-a"}, {101: "start-a", 102: "start-b"},
                                   {101: "start-a", 102: "start-b"}]
        _terminate_linux_tree(100)
        group.assert_has_calls([call(100, 19), call(100, 9)])
        self.assertEqual(send.call_args_list[-2:], [
            call(102, "start-b", 9), call(101, "start-a", 9),
        ])

    @patch("adaptive_qa.browser_process.os.kill")
    @patch("adaptive_qa.browser_process._linux_identity", return_value="new-start")
    def test_reused_pid_is_not_signalled(self, identity, kill):
        _signal_linux_process(101, "old-start", 9)
        kill.assert_not_called()

    @patch("adaptive_qa.browser_process.os.killpg", create=True)
    @patch("adaptive_qa.browser_process._signal_linux_process")
    @patch("adaptive_qa.browser_process._linux_descendants")
    def test_unstable_tree_raises_after_attempting_cleanup(self, descendants, send, group):
        descendants.side_effect = [{number: str(number)} for number in range(101, 106)]
        with self.assertRaisesRegex(RuntimeError, "stabilize"):
            _terminate_linux_tree(100)
        group.assert_any_call(100, 9)
        self.assertTrue(any(item.args[2] == 9 for item in send.call_args_list))


if __name__ == "__main__":
    unittest.main()
