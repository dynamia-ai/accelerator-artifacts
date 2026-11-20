include ../../../scripts/component.mk

UPSTREAM_COMMIT := 99fc48a1c1509e7fc7eefac8d334a7f0547adb0b
UPSTREAM_CHART := deployment/mx-exporter/helm/mx-exporter

.PHONY: chart
chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	curl --fail --silent --show-error --location --retry 3 \
		--output "$$tmp/source.tgz" "https://codeload.github.com/MetaX-MACA/mxExporter/tar.gz/$(UPSTREAM_COMMIT)"; \
	root="mxExporter-$(UPSTREAM_COMMIT)"; \
	tar -xzf "$$tmp/source.tgz" -C "$$tmp" --strip-components=1 \
		"$$root/$(UPSTREAM_CHART)"; \
	chart="$$tmp/$(UPSTREAM_CHART)"; \
	yq -e '.name == "mx-exporter" and .version == "0.8.1" and .appVersion == "2.2.11"' "$$chart/Chart.yaml" >/dev/null; \
	version="$(patsubst v%,%,$(VERSION))"; \
	IMAGE_TAG="$$version" yq -i '.image.tag = strenv(IMAGE_TAG)' "$$chart/values.yaml"; \
	cp LICENSE "$$chart/"; \
	helm lint --strict "$$chart"; \
	mkdir -p "$(OUT)/mx-exporter"; \
	helm package "$$chart" --version "$$version" --app-version "$$version" --destination "$(OUT)/mx-exporter"
