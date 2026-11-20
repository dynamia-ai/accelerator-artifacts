# Dynamia Accelerator Artifacts

本仓库按厂商和组件管理 Kubernetes Device Plugin 与硬件指标 Exporter，通过 GitHub Container Registry（GHCR）分发获准公开的应用镜像和 OCI Helm Chart。

| 厂商 | 组件 | 产物与状态 |
| --- | --- | --- |
| 海光 HCU | [Device Plugin](vendors/hygon/hcu-device-plugin/README.md)、[Exporter](vendors/hygon/hcu-exporter/README.md) | 各 1 个应用镜像。配方使用官方 `v3.0.2` 镜像包，公开再分发待确认。 |
| 华为昇腾 | [NPU Exporter](vendors/ascend/npu-exporter/README.md) | 1 个 OCI Helm Chart。配方使用 MindCluster `v26.2.0` 子 Chart，集群直接从 AscendHub 拉取镜像。 |
| 寒武纪 MLU | [Device Plugin 与 MLU Exporter](vendors/cambricon/README.md) | 官方构建和安装入口。 |

## 本地构建

准备 Python 3.15、GNU Make、Bash 4 或以上版本。应用镜像配方需要 Skopeo，Chart 配方需要 Helm 和 Mike Farah 的 yq。

```bash
make -C vendors/hygon/hcu-device-plugin app
make -C vendors/ascend/npu-exporter chart
```

产物写到各组件的 `dist/`。运行以下命令可复用公开 CI 的组件清单和校验入口。

```bash
uv run --locked python scripts/components.py matrix
uv run --locked python scripts/components.py build ascend/npu-exporter
uv run --locked python -m unittest discover -s tests
```

[目录约定与厂商接入计划](docs/accelerator-artifacts-design.md) · [发布操作](docs/operations.md) · [贡献规则](CONTRIBUTING.md)
