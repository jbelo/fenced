# Sourced by run-shell; keep template integration in the extra.
if [[ "${MEMTY_ENABLE:-1}" != 0 ]]; then
  memty_source=${MEMTY_SOURCE:-"$HOME/personal/memty"}
  if [[ -d "$memty_source" && -r "$memty_source/AGENTS.md" ]]; then
    memty_source=$(cd -- "$memty_source" && pwd -P)
    case "$memty_source,$agent_home" in
      *,*,*) printf 'error: Memty mount paths containing commas are unsupported\n' >&2; exit 1 ;;
    esac
    docker_args+=(--mount "type=bind,src=$memty_source,target=$agent_home/memty,readonly")
  elif [[ -n "${MEMTY_SOURCE:-}" ]]; then
    printf 'error: Memty source must contain readable AGENTS.md: %s\n' "$memty_source" >&2
    exit 1
  else
    printf 'warning: Memty template unavailable at %s\n' "$memty_source" >&2
  fi
fi
