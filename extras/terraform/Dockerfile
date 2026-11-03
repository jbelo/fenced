ARG BASE_IMAGE=go-agent
FROM ${BASE_IMAGE} AS terraform-builder

ARG TARGETARCH
# Pinned release and SHA256 checksums from releases.hashicorp.com.
RUN set -eux; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) checksum=1ce994251c00281d6845f0f268637ba50c0005657eb3cf096b92f753b42ef4dc ;; \
      arm64) checksum=a43d1d0da9b9bab214a8305a39db0e40869572594ccf50c416a7756499143633 ;; \
      *) echo "unsupported architecture=$arch" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends unzip; \
    curl -fL --retry 3 -o /tmp/terraform.zip \
      "https://releases.hashicorp.com/terraform/1.11.4/terraform_1.11.4_linux_${arch}.zip"; \
    printf '%s  /tmp/terraform.zip\n' "$checksum" | sha256sum -c -; \
    unzip /tmp/terraform.zip terraform -d /tmp/terraform; \
    install -m 0755 /tmp/terraform/terraform /usr/local/bin/terraform

FROM ${BASE_IMAGE}
COPY --from=terraform-builder /usr/local/bin/terraform /usr/local/bin/terraform
RUN CHECKPOINT_DISABLE=1 terraform version
