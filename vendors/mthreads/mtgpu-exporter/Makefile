include ../../../scripts/component.mk

IMAGE_DIGEST_v2.1.0 := sha256:610c146c3caaeec4c32985b47b674d9f7a0644ba88ea1b7fd5eb4c704e5787a5
IMAGE_DIGEST := $(IMAGE_DIGEST_$(VERSION))
IMAGE_SOURCE := docker://registry.mthreads.com/mcconline/mtgpu-exporter@$(IMAGE_DIGEST)

.PHONY: app
app:
	@set -euo pipefail; \
	if [ -z "$(IMAGE_DIGEST)" ]; then \
		printf 'No pinned mtgpu-exporter image digest for %s\n' "$(VERSION)" >&2; \
		exit 1; \
	fi; \
	actual=$$(skopeo inspect --raw "$(IMAGE_SOURCE)" | skopeo manifest-digest /dev/stdin); \
	test "$$actual" = "$(IMAGE_DIGEST)"; \
	mkdir -p "$(OUT)/mtgpu-exporter"; \
	cp LICENSE "$(OUT)/mtgpu-exporter/LICENSE"; \
	printf '%s\n' "$(IMAGE_SOURCE)" > "$(OUT)/mtgpu-exporter/image-source"
