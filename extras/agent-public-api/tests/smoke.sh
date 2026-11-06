#!/usr/bin/env bash
# Offline toolchain check; never resolves project dependencies or contacts services.
set -euo pipefail
mkdir -p "$HOME"
java -version
javac -version
clojure -Sdescribe
rlwrap --version
ssh -V
ssh -G -F /dev/null example.invalid >/dev/null
test "$(id -un)" = "agent-$(id -u)"
openssl version
make --version
git --version
go version
node --version
tmux -V
command -v clj public-api-clojure zip unzip

# Use the bundled CLI runtime so this check needs neither Maven access nor caches.
tools_jars=(/usr/local/lib/clojure/libexec/clojure-tools-*.jar)
[[ ${#tools_jars[@]} -eq 1 && -f ${tools_jars[0]} ]]
clojure -Srepro -Scp "${tools_jars[0]}" -M -e \
  '(assert (= 42 (+ 20 22)))
   (assert (= (System/getenv "HOME") (System/getProperty "user.home")))
   (println "Clojure execution and JVM home verified")'
