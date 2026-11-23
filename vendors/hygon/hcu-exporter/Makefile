include ../../../scripts/component.mk

UPSTREAM_COMMIT := 30cfbc1031957737731725ceddb663bc508d7c96
UPSTREAM_CHART := deployment/helm/hcu-exporter
CHART_ARTIFACT := hcu-exporter-charts
CHART_VERSION := $(patsubst v%,%,$(VERSION))

CHART_METADATA := .apiVersion = "v2" | .name = strenv(CHART_ARTIFACT) | .version = strenv(CHART_VERSION) | \
	.annotations."dynamia.ai/redistribution-changes" = "Dynamia adapted the Chart metadata for OCI packaging."
CHART_DEFAULTS := .hcuExporter.hcuExporter.image.repository = "ghcr.io/dynamia-ai/hygon/hcu-exporter" | \
	.hcuExporter.nodeSelector."kubernetes.io/arch" = "amd64" | \
	(.hcuExporter.ports[] | select(.name == "metrics")).targetPort = "metrics" | .imagePullSecrets = [] | \
	(head_comment) as $$existing | . head_comment = ($$existing + "\nDynamia adapted the packaged defaults.")
CHECK_RENDER := select(.kind == "DaemonSet") | \
	[(.spec.selector.matchLabels | has("app.kubernetes.io/version") | not), \
	(.spec.template.spec.containers[0].image == "ghcr.io/dynamia-ai/hygon/hcu-exporter:2026"), \
	(.spec.template.metadata.annotations."prometheus.io/port" == "16081"), \
	(.spec.template.spec.containers[0].ports[0].hostPort == 16081)] | all

.PHONY: app chart
app:
	bash ../../../scripts/import-image.sh \
		"https://github.com/HYGON-AI/hcu-exporter/releases/download/$(VERSION)/hcu-exporter-$(VERSION).tar" \
		c0acb7520c040cfc1298bf6e1bcc7cca13064419592145ce025d786091cade26 \
		"$(OUT)/hcu-exporter" linux/amd64

chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	curl --fail --silent --show-error --location --retry 3 \
		--output "$$tmp/source.tgz" "https://codeload.github.com/HYGON-AI/hcu-exporter/tar.gz/$(UPSTREAM_COMMIT)"; \
	tar -xzf "$$tmp/source.tgz" -C "$$tmp" --strip-components=1 \
		"hcu-exporter-$(UPSTREAM_COMMIT)/$(UPSTREAM_CHART)" \
		"hcu-exporter-$(UPSTREAM_COMMIT)/NOTICE"; \
	chart="$$tmp/$(UPSTREAM_CHART)"; \
	UPSTREAM_VERSION="$(VERSION)" yq -e '.name == "hcu-exporter" and .appVersion == strenv(UPSTREAM_VERSION)' "$$chart/Chart.yaml" >/dev/null; \
	CHART_VERSION="$(CHART_VERSION)" CHART_ARTIFACT="$(CHART_ARTIFACT)" yq -i \
		'$(CHART_METADATA)' "$$chart/Chart.yaml"; \
	yq -i '$(CHART_DEFAULTS)' "$$chart/values.yaml"; \
	patch -d "$$chart" -p1 < standalone.patch; \
	cp LICENSE "$$tmp/NOTICE" "$$chart/"; \
	helm lint --strict "$$chart"; \
	helm template hcu-exporter "$$chart" \
		--set-string hcuExporter.hcuExporter.image.tag=2026 \
		--set hcuExporter.hcuExporter.env.hcuExporterListen=16081 | \
		yq eval-all -e '$(CHECK_RENDER)' - >/dev/null; \
	mkdir -p "$(OUT)/$(CHART_ARTIFACT)"; \
	helm package "$$chart" --destination "$(OUT)/$(CHART_ARTIFACT)"
