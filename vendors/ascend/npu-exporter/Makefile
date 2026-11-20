include ../../../scripts/component.mk

UPSTREAM_COMMIT := 6cb6683c8b73d1c26341bb81a2c1cefe12a855ca

.PHONY: chart
chart:
	@set -euo pipefail; \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	curl --fail --silent --show-error --location --retry 3 \
		--output "$$tmp/source.tgz" "https://codeload.github.com/Ascend/mind-cluster/tar.gz/$(UPSTREAM_COMMIT)"; \
	root="mind-cluster-$(UPSTREAM_COMMIT)"; \
	tar -xzf "$$tmp/source.tgz" -C "$$tmp" --strip-components=1 \
		"$$root/LICENSE" "$$root/component/npu-exporter/build" \
		"$$root/helm-deploy-tool/build" "$$root/helm-deploy-tool/app/values.yaml" \
		"$$root/helm-deploy-tool/app/charts/npu-exporter"; \
	deploy="$$tmp/helm-deploy-tool"; \
	chart="$$deploy/app/charts/npu-exporter"; \
	version="$(patsubst v%,%,$(VERSION))"; \
	CHART_VERSION="$$version" yq -e '.version == strenv(CHART_VERSION)' "$$chart/Chart.yaml" >/dev/null; \
	bash "$$deploy/build/split_yaml.sh"; \
	python3 "$$deploy/build/replace_yaml_values.py" --version "$(VERSION)" "$$deploy/app/charts"; \
	PARENT_VALUES="$$deploy/app/values.yaml" yq -i 'load(strenv(PARENT_VALUES))."npu-exporter" as $$parent | .image = $$parent.image | .is310P1usoc = $$parent.is310P1usoc' "$$chart/values.yaml"; \
	patch -d "$$chart" -p1 < standalone.patch; \
	cp "$$tmp/LICENSE" "$$chart/"; \
	cp LICENSING.md "$$chart/REDISTRIBUTION.md"; \
	helm lint --strict "$$chart"; \
	expected_image=$$(yq -r '.image.repository + ":" + .image.tag' "$$chart/values.yaml"); \
	for mode in false true; do \
		helm template npu-exporter "$$chart" --set "is310P1usoc=$$mode" | \
			EXPECTED_IMAGE="$$expected_image" yq eval-all -e '[select(.kind == "DaemonSet") | .spec.template.spec | (.initContainers[], .containers[]) | .image] | (length > 0 and (map(. == strenv(EXPECTED_IMAGE)) | all))' - > /dev/null; \
	done; \
	mkdir -p "$(OUT)/npu-exporter"; \
	helm package "$$chart" --destination "$(OUT)/npu-exporter"
