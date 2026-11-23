include ../../../scripts/component.mk

BUILDKIT_IMAGE := docker.io/moby/buildkit:buildx-stable-1@sha256:baf6138eb8c37644800c7c913fba051e840ebb9ba13eaf92d92ef9a1712d0b4c
CHART_ARTIFACT := gcu-exporter-charts
CHART_VERSION := $(patsubst v%,%,$(VERSION))

CHECK_ARM64_RENDER := select(.kind == "DaemonSet") | .spec.template.spec | \
	[(.nodeSelector."kubernetes.io/arch" == "arm64"), \
	(.volumes | map(select(.name == "libefml")) | .[0].hostPath.path == "/usr/lib/libefml-arm.so"), \
	(.containers[0].volumeMounts | map(select(.name == "libefml")) | .[0].mountPath == "/usr/lib/libefml.so")] | all

.PHONY: app chart
app:
ifneq ($(origin VERSION),file)
	$(error Set the gcu-exporter version in component.toml)
endif
ifneq ($(VERSION),v3.6.5)
	$(error No gcu-exporter source pin for $(VERSION). Dockerfile pins v3.6.5)
endif
	@set -eu; \
		out="$(OUT)/gcu-exporter"; \
		tmp=$$(mktemp -d); \
		builder="enflame-$$(basename "$$tmp")"; \
		export BUILDX_CONFIG="$$tmp/buildx"; \
		trap 'docker buildx rm "$$builder" >/dev/null || true; rm -rf "$$tmp"' EXIT; \
		docker buildx create --name "$$builder" --driver docker-container \
			--driver-opt "image=$(BUILDKIT_IMAGE)"; \
		docker buildx build --builder "$$builder" --provenance=false --sbom=false \
			--build-arg "EXPORTER_VERSION=$(VERSION)" --build-arg SOURCE_DATE_EPOCH=1762500735 \
			--tag "gcu-exporter:$(VERSION)" \
			--output "type=oci,dest=$$tmp/image.tar,rewrite-timestamp=true" - < Dockerfile; \
		mkdir -p "$$out"; \
		source="oci:$$out/image:gcu-exporter"; \
		skopeo copy --preserve-digests "oci-archive:$$tmp/image.tar" "$$source"; \
		{ cat LICENSE; printf '\n'; cat SOURCES.md; } > "$$out/LICENSE"; \
		printf '%s\n' "$$source" > "$$out/image-source"

chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	cp -R "chart/$(CHART_ARTIFACT)" "$$tmp/"; \
	chart="$$tmp/$(CHART_ARTIFACT)"; \
	cp LICENSE "$$chart/"; \
	helm lint --strict "$$chart"; \
	helm template gcu-exporter "$$chart" --set architecture=arm64 | \
		yq eval-all -e '$(CHECK_ARM64_RENDER)' - >/dev/null; \
	mkdir -p "$(OUT)/$(CHART_ARTIFACT)"; \
	helm package "$$chart" --version "$(CHART_VERSION)" --app-version "$(VERSION)" \
		--destination "$(OUT)/$(CHART_ARTIFACT)"
