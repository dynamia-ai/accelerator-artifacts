include ../../../scripts/component.mk

.PHONY: app
app:
	bash ../../../scripts/import-image.sh \
		"https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/download/$(VERSION)/hcu-device-plugin-$(VERSION).tar" \
		d23b5c1507821fdc9b2fd5440bee8f5818d2584d545bc2f0ef5e44a7595019ef \
		"$(OUT)/hcu-device-plugin" linux/amd64
