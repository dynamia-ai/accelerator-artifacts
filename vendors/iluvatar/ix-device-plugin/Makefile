include ../artifacts.mk

IMAGE_ARTIFACT := device-plugin
IMAGE_REPOSITORY := k8s/ix-device-plugin
IMAGE_SHA256 := 5b60c3a70173bc093592ab195daedb84a9e8b6e5a576d40997f608761e3dafc2

CHART_URL := https://github.com/Deep-Spark/ix-device-plugin/releases/download/$(VERSION)/ix-device-plugin-$(CHART_VERSION).tgz
CHART_SHA256 := 4fc66eb48cd1efbd5d5d86d7124d1b651b6c9257b951d5375d40624bf8caea3e

.PHONY: chart
chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	$(call fetch_verified,$(CHART_URL),$$tmp/chart.tgz,$(CHART_SHA256)); \
	tar -xzf "$$tmp/chart.tgz" -C "$$tmp"; \
	chart="$$tmp/ix-device-plugin"; \
	cp LICENSE "$$chart/"; \
	helm lint --strict "$$chart"; \
	helm package "$$chart" --destination "$(OUT)/ix-device-plugin"
