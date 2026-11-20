include ../../../scripts/component.mk

CHART_VERSION := $(patsubst v%,%,$(VERSION))

define verify_sha256
printf '%s  %s\n' "$(1)" "$(2)" | shasum -a 256 --check --status
endef

define fetch_verified
curl --fail --silent --show-error --location --retry 3 --output "$(2)" "$(1)"; \
$(call verify_sha256,$(3),$(2))
endef

.PHONY: app
app:
	@set -euo pipefail; \
	ref="docker://registry.iluvatar.com.cn:10443/$(IMAGE_REPOSITORY)@sha256:$(IMAGE_SHA256)"; \
	skopeo inspect --raw "$$ref" >/dev/null; \
	mkdir -p "$(OUT)/$(IMAGE_ARTIFACT)"; \
	printf '%s\n' "$$ref" > "$(OUT)/$(IMAGE_ARTIFACT)/image-source"
