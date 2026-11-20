SHELL := bash

OUTPUT_DIR ?= dist
OUT := $(abspath $(OUTPUT_DIR))
VERSION := $(shell python3 -c 'import tomllib; print(tomllib.load(open("component.toml", "rb"))["version"])')
