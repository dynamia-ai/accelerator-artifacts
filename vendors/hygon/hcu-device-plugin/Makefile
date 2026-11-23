include ../../../scripts/component.mk

UPSTREAM_COMMIT := 9e9870a277b7038ab924ded3df7c44289c846858
UPSTREAM_CHARTS := deployment/helm
CHARTS := k8s-hcu-plugin k8s-hcu-plugin-hami k8s-hcu-plugin-mig
CHART_VERSION := $(patsubst v%,%,$(VERSION))

.PHONY: app chart
app:
	bash ../../../scripts/import-image.sh \
		"https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/download/$(VERSION)/hcu-device-plugin-$(VERSION).tar" \
		d23b5c1507821fdc9b2fd5440bee8f5818d2584d545bc2f0ef5e44a7595019ef \
		"$(OUT)/hcu-device-plugin" linux/amd64

chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	curl --fail --silent --show-error --location --retry 3 \
		--output "$$tmp/source.tgz" "https://codeload.github.com/HYGON-AI/k8s-hcu-device-plugin/tar.gz/$(UPSTREAM_COMMIT)"; \
	tar -xzf "$$tmp/source.tgz" -C "$$tmp" --strip-components=1 \
		"k8s-hcu-device-plugin-$(UPSTREAM_COMMIT)/$(UPSTREAM_CHARTS)"; \
	patch -d "$$tmp/$(UPSTREAM_CHARTS)" -p1 < standalone.patch; \
	for name in $(CHARTS); do \
		chart="$$tmp/$(UPSTREAM_CHARTS)/$$name"; \
		UPSTREAM_VERSION="$(VERSION)" CHART_NAME="$$name" yq -e \
			'.name == strenv(CHART_NAME) and .appVersion == strenv(UPSTREAM_VERSION)' "$$chart/Chart.yaml" >/dev/null; \
		CHART_VERSION="$(CHART_VERSION)" yq -i '.version = strenv(CHART_VERSION) | \
			.annotations."dynamia.ai/redistribution-changes" = "Dynamia normalized the version for OCI packaging."' "$$chart/Chart.yaml"; \
		key=hcuDevicePlugin; \
		if [ "$$name" = k8s-hcu-plugin-mig ]; then key=hcuDevicePluginMig; fi; \
		CHART_VALUES_KEY="$$key" yq -i '.[strenv(CHART_VALUES_KEY)].hcuDpCntr.image.repository = "ghcr.io/dynamia-ai/hygon/hcu-device-plugin" | \
			.[strenv(CHART_VALUES_KEY)].nodeSelector."kubernetes.io/arch" = "amd64" | .imagePullSecrets = [] | \
			(head_comment) as $$existing | . head_comment = ($$existing + "\nDynamia adapted the packaged defaults.")' "$$chart/values.yaml"; \
		cp LICENSE "$$chart/"; \
		helm lint --strict "$$chart"; \
		helm template "$$name" "$$chart" > "$$tmp/rendered.yaml"; \
		IMAGE_TAG="$(VERSION)" yq eval-all -e 'select(.kind == "DaemonSet") | .spec.template.spec | \
			[(.nodeSelector."kubernetes.io/arch" == "amd64"), \
			(.containers[0].image == ("ghcr.io/dynamia-ai/hygon/hcu-device-plugin:" + strenv(IMAGE_TAG)))] | all' "$$tmp/rendered.yaml" >/dev/null; \
		if [ "$$name" = k8s-hcu-plugin-hami ]; then \
			yq eval-all -e 'select(.kind == "ClusterRole") | .rules | \
				[(map(select(.resources[] == "pods")) | .[0].verbs | contains(["delete"])), \
				(map(select(.resources[] == "configmaps")) | .[0].verbs | contains(["get", "create", "patch"]))] | all' \
				"$$tmp/rendered.yaml" >/dev/null; \
		fi; \
		mkdir -p "$(OUT)/$$name"; \
		helm package "$$chart" --destination "$(OUT)/$$name"; \
	done
