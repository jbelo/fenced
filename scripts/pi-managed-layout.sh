# Managed layout helpers from https://pi.dev/install.sh (reviewed 2026-11-10).
# Keep compatible with upstream pi update: releases-v1, schemaVersion 1.
validate_managed_install_artifacts() {
  package_json_path="$1"
  package_lock_path="$2"
  managed_version="$3"

  node - "$package_json_path" "$package_lock_path" "$PI_PACKAGE" "$managed_version" <<'NODE'
const fs = require("node:fs");
const packageJson = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const packageLock = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const piPackage = process.argv[4];
const version = process.argv[5];
const root = packageLock.packages?.[""];
const piEntry = packageLock.packages?.[`node_modules/${piPackage}`];

if (packageJson.version !== version || packageJson.dependencies?.[piPackage] !== version) {
	throw new Error(`managed installer package.json must describe ${piPackage}@${version}`);
}
if (packageLock.lockfileVersion !== 3) {
	throw new Error("managed installer package-lock.json must use lockfileVersion 3");
}
if (packageLock.version !== version || root?.version !== version || root?.dependencies?.[piPackage] !== version) {
	throw new Error(`managed installer package-lock.json root must describe ${piPackage}@${version}`);
}
if (piEntry?.version !== version) {
	throw new Error(`managed installer package-lock.json does not include ${piPackage}@${version}`);
}
NODE
}

write_managed_install_marker() {
  managed_root="$1"
  managed_entrypoint_type="$2"
  managed_entrypoint_path="$3"
  marker_tmp="$managed_root/$PI_MANAGED_INSTALL_MARKER.tmp.$$"

  node - "$marker_tmp" "$managed_entrypoint_type" "$managed_entrypoint_path" <<'NODE'
const fs = require("node:fs");
const markerPath = process.argv[2];
const entrypointType = process.argv[3];
const entrypointPath = process.argv[4];
fs.writeFileSync(
	markerPath,
	`${JSON.stringify(
		{
			kind: "pi-managed-install",
			schemaVersion: 1,
			layout: "releases-v1",
			entrypoint: { type: entrypointType, path: entrypointPath },
		},
		null,
		2,
	)}\n`,
);
NODE
  mv -f "$marker_tmp" "$managed_root/$PI_MANAGED_INSTALL_MARKER"
}

managed_install_entrypoint_path() {
  managed_root="$1"

  node - "$managed_root/$PI_MANAGED_INSTALL_MARKER" <<'NODE'
const fs = require("node:fs");
const marker = JSON.parse(fs.readFileSync(process.argv[2], "utf8").replace(/^\uFEFF/, ""));
if (typeof marker.entrypoint?.path !== "string" || !marker.entrypoint.path) process.exit(1);
console.log(marker.entrypoint.path);
NODE
}

write_managed_install_launcher() {
  managed_agent_dir="$1"
  managed_launcher_dir="$managed_agent_dir/bin"
  managed_launcher="$managed_launcher_dir/$PI_CMD"
  launcher_tmp="$managed_launcher.tmp.$$"

  # Callers verified the managed marker, so an existing launcher is ours and is
  # rewritten to pick up launcher fixes on reinstall.
  if [ -e "$managed_launcher" ] && [ ! -f "$managed_launcher" ]; then
    return 1
  fi

  mkdir -p "$managed_launcher_dir"
  cat >"$launcher_tmp" <<'EOF'
#!/bin/sh
case "$0" in
  */*) pi_launcher="$0" ;;
  *) pi_launcher=$(command -v "$0") || exit 127 ;;
esac
while [ -L "$pi_launcher" ]; do
  pi_link=$(readlink "$pi_launcher") || exit 1
  case "$pi_link" in
    /*) pi_launcher="$pi_link" ;;
    *) pi_launcher=${pi_launcher%/*}/$pi_link ;;
  esac
done
pi_bin_dir=${pi_launcher%/*}
pi_agent_dir=${pi_bin_dir%/*}
pi_current_file=$pi_agent_dir/install/current-version
if ! IFS= read -r pi_current_version < "$pi_current_file"; then
  printf 'Could not read managed Pi version from %s.\n' "$pi_current_file" >&2
  exit 1
fi
case "$pi_current_version" in
  ""|.|..|*[!0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz._+-]*)
    printf 'Managed Pi version file is invalid: %s\n' "$pi_current_file" >&2
    exit 1
    ;;
esac
pi_release_dir=$pi_agent_dir/install/releases/$pi_current_version
pi_release_bin=$pi_release_dir/node_modules/.bin/pi
if [ ! -x "$pi_release_bin" ]; then
  printf 'Managed Pi executable is missing: %s\n' "$pi_release_bin" >&2
  exit 1
fi
# Node.js installed by the Pi installer is not added to shell profiles, so put
# it on PATH for pi's shebang and for child processes: npm in pi update and
# commands run through pi's bash tool.
pi_node_bin=${XDG_DATA_HOME:-$HOME/.local/share}/pi-node/current/bin
if [ -x "$pi_node_bin/node" ]; then
  PATH=$pi_node_bin:$PATH
  export PATH
fi
PI_MANAGED_INSTALL_ROOT=$pi_agent_dir/install
export PI_MANAGED_INSTALL_ROOT
exec "$pi_release_bin" "$@"
EOF
  chmod 755 "$launcher_tmp"
  mv -f "$launcher_tmp" "$managed_launcher"
}

write_managed_install_link() {
  managed_agent_dir="$1"
  managed_bin_dir="$2"
  managed_launcher="$managed_agent_dir/bin/$PI_CMD"
  managed_entrypoint="$managed_bin_dir/$PI_CMD"

  if [ "$managed_entrypoint" = "$managed_launcher" ]; then
    return 0
  fi
  mkdir -p "$managed_bin_dir"
  if [ -e "$managed_entrypoint" ] && [ ! -L "$managed_entrypoint" ]; then
    printf 'Refusing to replace the executable at %s.\n' "$managed_entrypoint" >&2
    return 1
  fi

  managed_link_target=$(node - "$managed_bin_dir" "$managed_launcher" <<'NODE'
const path = require("node:path");
console.log(path.relative(process.argv[2], process.argv[3]));
NODE
  )
  managed_link_tmp="$managed_bin_dir/.$PI_CMD.tmp.$$"
  rm -f "$managed_link_tmp"
  ln -s "$managed_link_target" "$managed_link_tmp"
  mv -f "$managed_link_tmp" "$managed_entrypoint"
}

write_managed_current_version() {
  managed_root="$1"
  managed_version="$2"
  current_tmp="$managed_root/current-version.tmp.$$"

  printf '%s\n' "$managed_version" >"$current_tmp"
  mv -f "$current_tmp" "$managed_root/current-version"
}

