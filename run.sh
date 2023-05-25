#!/bin/sh

set -ex

sha="${1:?needs sha}"

a="$(git log --format="%aI %s" "$sha"...master | uniq | wc -l)"
b="$(git log --oneline "$sha"...master | wc -l)"


if [ "$a" != "$b" ]; then
  echo 'nope'
  exit 1
fi

tmp_file="$(mktemp)"

git log --format="%H %cI %aI %s" "$sha"...master > "$tmp_file"

cat "$tmp_file"

git branch old_master

git filter-branch --env-filter 'export GIT_COMMITTER_DATE=$(fgrep -m 1 "$(git log -1 --format="%aI %s" $GIT_COMMIT)" '"$tmp_file"' | cut -d" " -f2)' -f "$sha"...master
