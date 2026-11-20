include ../../../scripts/component.mk

APP_IMAGE := docker.io/rocm/device-metrics-exporter
APP_VERSION := v1.5.3
APP_DIGEST := sha256:bdfc644bb8d4d07d9a0c31dda3e0d463101f48170548c5a7e7f7066c253fa813
APP_SOURCE := docker://$(APP_IMAGE)@$(APP_DIGEST)
CHART := device-metrics-exporter-charts
CHART_URL := https://rocm.github.io/device-metrics-exporter/charts/$(CHART)-$(VERSION).tgz
CHART_SHA256 := c653e9918a1f1d4d2021e775d3e2b3c953d686fcffd55f865e7562f5b76a7634
INIT_IMAGE := busybox:1.36

.PHONY: app chart
app:
	@set -euo pipefail; \
	if [[ "$(VERSION)" != "$(APP_VERSION)" ]]; then \
		printf 'Image digest is pinned for %s, not %s. Update the version and digest together.\n' "$(APP_VERSION)" "$(VERSION)" >&2; \
		exit 1; \
	fi; \
	metadata=$$(skopeo --override-os linux --override-arch amd64 inspect --no-tags \
		--format '{{.Digest}} {{.Os}}/{{.Architecture}}' "$(APP_SOURCE)"); \
	if [[ "$$metadata" != "$(APP_DIGEST) linux/amd64" ]]; then \
		printf 'Unexpected image digest or platform: %s\n' "$$metadata" >&2; \
		exit 1; \
	fi; \
	mkdir -p "$(OUTPUT_DIR)/device-metrics-exporter"; \
	printf '%s\n' "$(APP_SOURCE)" > "$(OUTPUT_DIR)/device-metrics-exporter/image-source"

chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	HELM_REPOSITORY_CONFIG="$$tmp/repositories.yaml" HELM_REPOSITORY_CACHE="$$tmp/cache" \
		helm pull "$(CHART_URL)" --destination "$$tmp"; \
	archive="$$tmp/$(CHART)-$(VERSION).tgz"; \
	printf '%s  %s\n' "$(CHART_SHA256)" "$$archive" | shasum -a 256 --check; \
	tar -xzf "$$archive" -C "$$tmp"; \
	chart="$$tmp/$(CHART)"; \
	NAME="$(CHART)" UPSTREAM_VERSION="$(VERSION)" yq -e \
		'.name == strenv(NAME) and .version == strenv(UPSTREAM_VERSION) and .appVersion == strenv(UPSTREAM_VERSION)' \
		"$$chart/Chart.yaml" >/dev/null; \
	version="$(patsubst v%,%,$(VERSION))"; \
	CHART_VERSION="$$version" CHANGE_NOTICE="Dynamia changed Chart.yaml version from $(VERSION) to $$version for OCI packaging." \
		yq -i '.version = strenv(CHART_VERSION) | .annotations."dynamia.ai/redistribution-changes" = strenv(CHANGE_NOTICE)' "$$chart/Chart.yaml"; \
	cp LICENSE "$$chart/LICENSE"; \
	helm lint --strict --kube-version 1.29.0 "$$chart"; \
	images=$$(helm template exporter "$$chart" --namespace kube-amd-gpu --kube-version 1.29.0 | \
		yq eval-all -r 'select(.kind == "DaemonSet") | .spec.template.spec | (.initContainers[], .containers[]) | .image' -); \
	expected=$$(printf '%s\n' "$(INIT_IMAGE)" "$(APP_IMAGE):$(VERSION)"); \
	if [[ "$$images" != "$$expected" ]]; then \
		printf 'Unexpected Chart images:\n%s\n' "$$images" >&2; \
		exit 1; \
	fi; \
	mkdir -p "$(OUTPUT_DIR)/$(CHART)"; \
	helm package "$$chart" --destination "$(OUTPUT_DIR)/$(CHART)"
