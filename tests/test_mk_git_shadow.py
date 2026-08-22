from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Union


SCRIPT = Path(__file__).parents[1] / "mk-git-shadow"


def run(
    *args: Union[str, Path], cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("git", *args, cwd=repo, check=check)


class MkGitShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def init_repo(self, name: str = "repo", *, commit: bool = True) -> Path:
        repo = self.root / name
        repo.mkdir()
        git(repo, "init", "--quiet")
        git(repo, "config", "user.name", "Test User")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "checkout", "--quiet", "-b", "main")
        if commit:
            (repo / "tracked").write_text("content\n")
            git(repo, "add", "tracked")
            git(repo, "commit", "--quiet", "-m", "initial")
        return repo

    def create_shadow(self, repo: Path, path: str = ".shadow") -> None:
        run(sys.executable, SCRIPT, path, cwd=repo)

    def test_unborn_branch(self) -> None:
        repo = self.init_repo(commit=False)
        self.create_shadow(repo)

        result = git(repo, "--git-dir=.shadow", "symbolic-ref", "HEAD")
        self.assertEqual(result.stdout.strip(), "refs/heads/main")

    def test_packed_current_branch(self) -> None:
        repo = self.init_repo()
        expected = git(repo, "rev-parse", "HEAD").stdout.strip()
        git(repo, "pack-refs", "--all")
        self.create_shadow(repo)

        actual = git(repo, "--git-dir=.shadow", "rev-parse", "HEAD")
        self.assertEqual(actual.stdout.strip(), expected)

    def test_nested_reference_path(self) -> None:
        repo = self.init_repo()
        expected = git(repo, "rev-parse", "HEAD").stdout.strip()
        (repo / "nested").mkdir()
        self.create_shadow(repo, "nested/.shadow")

        actual = git(repo, "--git-dir=nested/.shadow", "rev-parse", "HEAD")
        self.assertEqual(actual.stdout.strip(), expected)
        git(repo, "--git-dir=nested/.shadow", "fsck", "--no-dangling")

    def test_source_linked_worktree(self) -> None:
        repo = self.init_repo()
        expected = git(repo, "rev-parse", "HEAD").stdout.strip()
        linked = self.root / "linked"
        git(repo, "worktree", "add", "--quiet", "-b", "linked", str(linked))
        self.create_shadow(linked)

        actual = git(linked, "--git-dir=.shadow", "rev-parse", "HEAD")
        self.assertEqual(actual.stdout.strip(), expected)

    def test_failure_has_no_traceback(self) -> None:
        result = run(
            sys.executable,
            SCRIPT,
            ".shadow",
            cwd=self.root,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("mk-git-shadow:", result.stderr)

    def test_rejects_repository_subdirectory(self) -> None:
        repo = self.init_repo()
        subdirectory = repo / "nested"
        subdirectory.mkdir()

        result = run(
            sys.executable,
            SCRIPT,
            ".shadow",
            cwd=subdirectory,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("repository root", result.stderr)
        self.assertFalse((subdirectory / ".shadow").exists())


if __name__ == "__main__":
    unittest.main()
