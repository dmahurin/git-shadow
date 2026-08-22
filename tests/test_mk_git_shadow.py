from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional, Union


SCRIPT = Path(__file__).parents[1] / "mk-git-shadow"


def run(
    *args: Union[str, Path],
    cwd: Path,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
        env=env,
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

    def create_shadow(
        self,
        repo: Path,
        path: str = ".shadow",
        *,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        run(sys.executable, SCRIPT, path, cwd=repo, env=env)

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

    def test_config_includes_are_removed(self) -> None:
        repo = self.init_repo()
        included_config = self.root / "included-config"
        included_config.write_text(
            '[remote "included"]\n'
            "\turl = https://example.invalid/repo.git\n"
        )
        git(repo, "config", "include.path", str(included_config))
        self.create_shadow(repo)

        remotes = git(repo, "--git-dir=.shadow", "remote")
        self.assertEqual(remotes.stdout, "")
        includes = git(
            repo,
            "--git-dir=.shadow",
            "config",
            "--get-regexp",
            r"^include(if)?\.",
            check=False,
        )
        self.assertEqual(includes.returncode, 1)

    def test_rejects_output_inside_source_git_directory(self) -> None:
        repo = self.init_repo()
        result = run(
            sys.executable,
            SCRIPT,
            ".git/shadow",
            cwd=repo,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("source Git directory", result.stderr)
        self.assertFalse((repo / ".git" / "shadow").exists())

    def test_failed_creation_leaves_no_output(self) -> None:
        repo = self.init_repo()
        wrapper_dir = self.root / "bin"
        wrapper_dir.mkdir()
        git_wrapper = wrapper_dir / "git"
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        git_wrapper.write_text(
            "#!/bin/sh\n"
            'case " $* " in *" reset "*) exit 42 ;; esac\n'
            f"exec {shlex.quote(real_git or 'git')} \"$@\"\n"
        )
        git_wrapper.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = f"{wrapper_dir}{os.pathsep}{environment['PATH']}"

        result = run(
            sys.executable,
            SCRIPT,
            ".shadow",
            cwd=repo,
            check=False,
            env=environment,
        )

        self.assertEqual(result.returncode, 42)
        self.assertFalse((repo / ".shadow").exists())
        self.assertFalse((repo / ".shadow_").exists())
        self.assertEqual(list(repo.glob("..shadow_.*")), [])

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
