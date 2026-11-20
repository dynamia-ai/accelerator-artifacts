FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.27.4-bookworm@sha256:4fa7c968ba93f1635670522dbb01a2c78150443e1385746924566079f36570ea AS build

ARG BUILDOS
ARG BUILDARCH
ARG TARGETOS
ARG TARGETARCH
ARG EXPORTER_VERSION
RUN test "$EXPORTER_VERSION" = v3.6.5 \
    && case "$TARGETOS/$TARGETARCH" in linux/amd64|linux/arm64) ;; *) exit 1 ;; esac \
    && test "$BUILDOS/$BUILDARCH" = "$TARGETOS/$TARGETARCH"

WORKDIR /src
ADD --checksum=sha256:82dbdca9e194afc61b9b61650f62202fbb31f5712ed633b128bfff055ea0082e \
    https://codeload.github.com/EnflameTechnology/gcu-exporter/tar.gz/a83264c908916e94480a42cddcd0615c56def9e6 /tmp/gcu-exporter.tar.gz

# Retain EFML function relocations for the upstream dlopen calls to resolve at runtime.
RUN --network=none tar -xzf /tmp/gcu-exporter.tar.gz --strip-components=1 \
    && CGO_ENABLED=1 GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off \
        CGO_LDFLAGS='-Wl,--export-dynamic -Wl,-z,lazy' \
        GOFLAGS='-mod=vendor -trimpath -buildvcs=false' make GCU_EXPORTER_VERSION="$EXPORTER_VERSION" \
    && readelf --relocs --wide gcu-exporter | grep -q 'JUMP_SLOT .* EfmlInit ' \
    && mkdir -p /licenses \
    && cp LICENSE LICENSE.md NOTICE /licenses/ \
    && cp /usr/local/go/LICENSE /licenses/GO-LICENSE \
    && find vendor -type f \( -iname 'license*' -o -iname 'copying*' -o -iname 'notice*' -o -iname 'copyright*' \) \
        -exec cp --parents -t /licenses {} +

FROM docker.io/library/debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc

ARG EXPORTER_VERSION
LABEL org.opencontainers.image.source="https://github.com/EnflameTechnology/gcu-exporter" \
    org.opencontainers.image.revision="a83264c908916e94480a42cddcd0615c56def9e6" \
    org.opencontainers.image.version="$EXPORTER_VERSION"

COPY --from=build /src/gcu-exporter /usr/bin/gcu-exporter
COPY --from=build /licenses/ /usr/share/doc/gcu-exporter/

EXPOSE 9400
ENTRYPOINT ["/usr/bin/gcu-exporter"]
