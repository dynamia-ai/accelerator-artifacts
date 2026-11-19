FROM docker.io/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS go-toolchain

FROM docker.io/library/ubuntu:22.04@sha256:9abcaffc92a5279fff3a6a41635c0800ea33e528425fb389658806476e7defde AS build
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=go-toolchain /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}" GOFLAGS="-mod=readonly" GOTOOLCHAIN="local"
WORKDIR /work
COPY source/ ./
ARG VERSION
RUN --mount=type=secret,id=cndev_header,target=/work/pkg/cndev/include/cndev.h,required=true \
    make build TARGETPLATFORM=linux/amd64 VERSION="$VERSION"

FROM docker.io/library/ubuntu:22.04@sha256:9abcaffc92a5279fff3a6a41635c0800ea33e528425fb389658806476e7defde
LABEL org.opencontainers.image.source="https://github.com/dynamia-ai/accelerator-artifacts"
COPY --from=build /work/k8s-device-plugin /usr/bin/k8s-device-plugin
COPY licenses/ /usr/share/doc/cambricon-device-plugin/
RUN --mount=type=secret,id=libcndev,required=true \
    --mount=type=secret,id=libcntopo,required=true \
    install -m 0644 /run/secrets/libcndev /usr/lib/libcndev.so \
    && install -m 0644 /run/secrets/libcntopo /usr/lib/libcntopo.so
CMD ["/usr/bin/k8s-device-plugin"]
