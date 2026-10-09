# SSH support for local service images

Reusable root, key-only SSH access for Debian/Ubuntu-based development images.
This is an image layer, not a separate service or an agent image extension.
The base go-agent already provides the SSH client and numeric-UID compatibility.

Build on a prepared application image:

```sh
docker build --build-arg BASE_IMAGE=my-service-runtime -t my-service-ssh extras/ssh
bash extras/ssh/scripts/setup-client.sh /absolute/path/to/ssh service.test service \
  '~/.config/service/ssh/id_ed25519'
```

The setup script preserves the client private key and regenerates its public key
and connection config. Install `client/id_ed25519` and `client/config` at the
chosen agent-home location, owned by the agent UID with mode 0600. Each extra
owns its paths and installation target; do not share private keys by accident.

Run the image on the internal network, mounting `server/authorized_keys`
read-only at `/etc/ssh/authorized_keys`. Supply the full application command
after the image name. The wrapper replaces both the upstream entrypoint and
default command; include any required upstream startup script explicitly.
An omitted command fails immediately. The image runs as root and needs writable
`/etc/ssh` and `/run` for server keys and startup state.

SSH starts in the background, then the application becomes PID 1. No supervisor
restarts SSH if it exits. Host keys persist only for the container lifetime;
the generated client config skips host-key verification for local development.
`StrictModes no` permits the host-owned, read-only authorized-key mount.
No ports are published by this layer. Full root access includes application data;
it is not a read-only log interface. Container shutdown removes SSH too.

Keep application repairs, configuration, data volumes, and lifecycle targets in
the consuming extra. XKS, for example, repairs upstream Perl before applying
this layer. Rebuild and recreate consuming containers to apply layer changes.
