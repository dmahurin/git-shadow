# mk-git-shadow

`mk-git-shadow` is a script that creates a *shadow* Git repository. It sets up a new git directory that **inherits objects from the current repository** via Git’s *alternates* feature and creates a worktree that points back to the current working directory.

This is useful in sandboxed or restricted environments where direct writes to the `.git` directory are prohibited or not desired. The shadow repository shares objects with the original repository while keeping its own history and configuration.

## Requirements and installation

`mk-git-shadow` requires Git and Python 3.9 or newer. Install it from a checkout with pip or pipx:

```sh
pip install .
# or
pipx install .
```

## Basic Usage

```sh
# Create a shadow repo `.xgit` in the current directory
mk-git-shadow .xgit
```

Run the command from the root of the source repository. The git-dir reference may be placed elsewhere by passing a different relative or absolute path.

This creates two entries:

- `.xgit` is a small gitdir file used with `GIT_DIR` or `--git-dir`.
- `.xgit_` contains the writable shadow repository metadata.

Once the shadow repository is created you can run Git commands against it by setting the `GIT_DIR` environment variable (or using the `--git-dir` option). For example:

```sh
# Commit changes in the shadow repository
GIT_DIR=.xgit git commit -a

# View log from the shadow repository
git --git-dir .xgit log
```

And later pull the changes from the shadow repository:

```sh
git pull .xgit
```

The shadow repository depends on the original repository's object database. It is not independently portable, and the original repository must remain available for the shadow to work.

## Use with OpenAI Codex

```sh
# Create a shadow repo for Codex
mk-git-shadow .aigit

# Run Codex inside the shadow environment
GIT_DIR=$(pwd)/.aigit codex ...

# Inspect the shadow repository state
git --git-dir .aigit log

# Merge changes back into the original repository
git pull .aigit
```
