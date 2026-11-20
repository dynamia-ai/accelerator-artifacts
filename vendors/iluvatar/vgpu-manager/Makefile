include ../artifacts.mk

IMAGE_ARTIFACT := gpu-manager
IMAGE_REPOSITORY := cloud/gpu-manager
IMAGE_SHA256 := e89fc5d078e64c059b4f18e8347d4f671bf9416d17cd410881e836286cdd7375

UPSTREAM_TAG := $(VERSION)-v5.0.1-r1
CHART_URL := https://gitee.com/deep-spark/iluvatar-vgpu-manager/releases/download/$(UPSTREAM_TAG)/iluvatar-vgpu-manager-$(CHART_VERSION).tgz
CHART_SHA256 := 9506d6bb0e93d31a26a574b9bc652a99ceb3b936079104c40e6176a0d432cf4b
NFD_ADAPTED_TEMPLATES := _helpers.tpl clusterrole.yaml clusterrolebinding.yaml master.yaml \
	nfd-gc.yaml nfd-master-conf.yaml post-delete-job.yaml serviceaccount.yaml

.PHONY: chart
chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	$(call fetch_verified,$(CHART_URL),$$tmp/chart.tgz,$(CHART_SHA256)); \
	tar -xzf "$$tmp/chart.tgz" -C "$$tmp"; \
	chart="$$tmp/iluvatar-vgpu-manager"; \
	cp LICENSE NFD-LICENSE NFD-ATTRIBUTION.md "$$chart/"; \
	for template in $(NFD_ADAPTED_TEMPLATES); do \
		file="$$chart/templates/ix-feature-discovery/$$template"; \
		printf '%s\n' '{{- /* Iluvatar adapted this file from Kubernetes SIGs Node Feature Discovery v0.18.3. Dynamia added this notice. See NFD-LICENSE and NFD-ATTRIBUTION.md. */ -}}' > "$$tmp/marked"; \
		cat "$$file" >> "$$tmp/marked"; \
		mv "$$tmp/marked" "$$file"; \
	done; \
	printf '%s\n' '{{- /* The Iluvatar namespace helper matches the namespace helper in Kubernetes SIGs Node Feature Discovery v0.18.3 with a renamed template. Dynamia added this notice. See NFD-LICENSE and NFD-ATTRIBUTION.md. */ -}}' > "$$tmp/marked"; \
	cat "$$chart/templates/_helpers.tpl" >> "$$tmp/marked"; \
	mv "$$tmp/marked" "$$chart/templates/_helpers.tpl"; \
	printf '%s\n' '# Iluvatar adapted the NFD settings in this file from Kubernetes SIGs Node Feature Discovery v0.18.3. Dynamia added this notice. See NFD-LICENSE and NFD-ATTRIBUTION.md.' > "$$tmp/marked"; \
	cat "$$chart/values.yaml" >> "$$tmp/marked"; \
	mv "$$tmp/marked" "$$chart/values.yaml"; \
	helm lint --strict "$$chart"; \
	helm package "$$chart" --destination "$(OUT)/iluvatar-vgpu-manager"
