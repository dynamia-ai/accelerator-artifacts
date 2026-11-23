include ../../../scripts/component.mk

APP_IMAGE := docker.io/rocm/device-metrics-exporter
APP_VERSION := v1.5.4
APP_DIGEST := sha256:435f01bb20470c905f65e5fa09756210030a96fd6c9c17ab1a0c4fb5cda9185c
APP_SOURCE := docker://$(APP_IMAGE)@$(APP_DIGEST)
CHART := device-metrics-exporter-charts
CHART_URL := https://rocm.github.io/device-metrics-exporter/charts/$(CHART)-$(VERSION).tgz
CHART_SHA256 := dcdabdab16d0de03aec2c492e5b95646e16f59c5205361aae73e3d20745c578a
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
