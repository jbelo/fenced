#!/usr/bin/env bash
# Offline regression test: cache selection, argument forwarding and Git relocation.
set -euo pipefail
extra_dir=$(cd "$(dirname "$0")/.." && pwd -P)
scratch=$(mktemp -d)
scratch=$(cd "$scratch" && pwd -P)
trap 'rm -rf -- "$scratch"' EXIT
repo="$scratch/checkout with spaces"
mkdir -p "$repo/modules/backend"
printf '{}\n' > "$repo/modules/backend/deps.edn"
git init -q "$repo"

# A fake CLI checks the wrapper contract without fetching any application dependencies.
cat > "$scratch/clojure-fixture" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
[[ $1 == -Sforce && $2 == -Sdeps && $4 == -P && $5 == -M:test ]]
[[ $3 == "{:mvn/local-repo \"$PUBLIC_API_SOURCE/.deps-cache/m2\"}" ]]
[[ $GITLIBS == "$PUBLIC_API_SOURCE/.deps-cache/gitlibs" ]]
[[ -f "$CLJ_CONFIG/deps.edn" ]]
[[ $(git config worktree.useRelativePaths) == true ]]
[[ $(git config fixture.preserved) == yes ]]
if [[ ${FIXTURE_FAIL:-0} == 1 ]]; then exit 42; fi
bare="$GITLIBS/_repos/fixture"
git init --bare -q "$bare"
tree=$(git --git-dir="$bare" mktree < /dev/null)
commit=$(printf 'fixture\n' | git -c user.name=Fixture -c user.email=fixture@example.invalid \
    --git-dir="$bare" commit-tree "$tree")
git --git-dir="$bare" worktree add --quiet --detach "$GITLIBS/libs/fixture/$commit" "$commit"
printf '%s\n' "$commit" > "$GITLIBS/fixture-commit"
EOF
chmod 755 "$scratch/clojure-fixture"
export PUBLIC_API_SOURCE="$repo"
export PUBLIC_API_CLOJURE="$scratch/clojure-fixture"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=fixture.preserved GIT_CONFIG_VALUE_0=yes
cd "$repo/modules/backend"
bash "$extra_dir/bin/public-api-clojure" -P -M:test
git -C "$repo" check-ignore -q .deps-cache/m2/example.jar
if FIXTURE_FAIL=1 bash "$extra_dir/bin/public-api-clojure" -P -M:test; then
    echo 'Expected failure was swallowed' >&2; exit 1
else
    [[ $? -eq 42 ]]
fi

cd "$scratch"
mv "$repo" "$scratch/relocated checkout"
repo="$scratch/relocated checkout"
commit=$(< "$repo/.deps-cache/gitlibs/fixture-commit")
[[ $(git -C "$repo/.deps-cache/gitlibs/libs/fixture/$commit" rev-parse HEAD) == "$commit" ]]
git --git-dir="$repo/.deps-cache/gitlibs/_repos/fixture" worktree list --porcelain | \
    grep -F "$repo/.deps-cache/gitlibs/libs/fixture/$commit" >/dev/null
echo 'Wrapper arguments, cache isolation, failures and relocated Git worktrees verified.'
