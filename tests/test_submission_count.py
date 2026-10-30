import unittest
from unittest.mock import Mock, patch

from joint_teapot.config import settings
from joint_teapot.teapot import Teapot
from joint_teapot.utils.joj3 import Env


class SubmissionCountTest(unittest.TestCase):
    def test_only_the_configured_course_test_repository_is_exempt(self):
        for org, repository, exempt in [
            ("ece482", "ece482/ece482-test", True),
            ("ece482", "ece482/p2team01", False),
            ("ece482", "student/ece482-test", False),
            ("ece482", "ece482/ece482-test-copy", False),
            ("ece482", "ece281/ece281-test", False),
            ("ece281", "ece281/ece281-test", True),
            ("", "/-test", False),
        ]:
            with self.subTest(org=org, repository=repository):
                teapot = Teapot()
                teapot._git = Mock()
                teapot._git.get_repo.return_value.iter_commits.return_value = []
                env = Env(github_actor="ta", github_repository=repository)
                with patch.object(settings, "gitea_org_name", org):
                    message, failed = teapot.joj3_check_submission_count(
                        env, "grading", "=0:1", "scoreboard.csv", True
                    )
                self.assertEqual(failed, not exempt)
                if exempt:
                    self.assertIn("Check Exempt", message)
                    teapot._git.get_repo.assert_not_called()
                else:
                    self.assertIn("exceeded", message)
                    teapot._git.get_repo.assert_called_once_with("grading")
