include ../artifacts.mk

IMAGE_ARTIFACT := exporter
IMAGE_REPOSITORY := k8s/ix-exporter
IMAGE_SHA256 := e2050e1f7b4213a5413294f7977db852a34d8b5924caaee9ec48c934fbaad40b

CHART_URL := https://github.com/Deep-Spark/ix-exporter/releases/download/$(VERSION)/ix-exporter-$(CHART_VERSION).tgz
CHART_SHA256 := ad2f427100a291f002af8af8ab03c6f2e63147b06c92fa24cffc5d904ad17f31

.PHONY: chart
chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	$(call fetch_verified,$(CHART_URL),$$tmp/chart.tgz,$(CHART_SHA256)); \
	tar -xzf "$$tmp/chart.tgz" -C "$$tmp"; \
	chart="$$tmp/ix-exporter"; \
	cp LICENSE "$$chart/"; \
	CHART_VERSION="$(CHART_VERSION)" yq -i '.version = strenv(CHART_VERSION) | .annotations."dynamia.ai/packaging-note" = "Dynamia updated Chart.yaml version from 1.0.0 to match the upstream release version."' "$$chart/Chart.yaml"; \
	helm lint --strict "$$chart"; \
	helm package "$$chart" --destination "$(OUT)/ix-exporter"
