#!/usr/bin/env bash
# Auto-sync password store with remote after every commit.
# Install as ~/.password-store/.git/hooks/post-commit (chmod +x)
#
# Why this approach instead of pass.git.pullAndPush:
# pass v1.7.4 supports the pass.git.pullAndPush config option syntactically,
# but the pass script's git_commit() function never actually reads it.
# This hook does the same thing and works on v1.7.4.

set -e

# Skip during rebase/merge/cherry-pick — those run hooks per-step
if [ -d "$(git rev-parse --git-path rebase-merge 2>/dev/null)" ] || \
   [ -d "$(git rev-parse --git-path rebase-apply 2>/dev/null)" ] || \
   [ -f "$(git rev-parse --git-path MERGE_HEAD 2>/dev/null)" ] || \
   [ -f "$(git rev-parse --git-path CHERRY_PICK_HEAD 2>/dev/null)" ]; then
    exit 0
fi

git pull --rebase origin master 2>/dev/null || true
git push origin master 2>&1
