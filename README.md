# mk-git-shadow

`mk-git-shadow` is a small shell script that creates a *shadow* Git repository. It sets up a new git directory that **inherits objects from the current repository** via Git’s *alternates* feature and creates a worktree that points back to the current working directory.

This is useful in sandboxed or restricted environments where direct writes to the `.git` directory are prohibited or not desired. The shadow repository shares objects with the original repository while keeping its own history and configuration.

## Basic Usage

```sh
# Create a shadow repo `.xgit` in the current directory
mk-git-shadow .xgit
```

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

## Use with OpenAI Codex

```sh
# Create a shadow repo for Codex
mk-git-shadow .aigit

# Run Codex inside the shadow environment
GIT_DIR=$(pwd)/.aigit npx @openai/codex ...

# Inspect the shadow repository state
git --git-dir .aigit log

# Merge changes back into the original repository
git pull .aigit
```
