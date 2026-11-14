# Read-only host-path metadata lets setup skills produce the correct host command.
# These paths grant no access to the host checkout or Docker socket.
docker_args+=(-e "FENCED_HOST_WORKSPACE=$workspace_root")
if [[ -n "${FENCED_HOST_CHECKOUT:-}" ]]; then
  docker_args+=(-e "FENCED_HOST_CHECKOUT=$FENCED_HOST_CHECKOUT")
fi
