# Dynamia Accelerator Artifacts

本仓库记录各厂商 Kubernetes Device Plugin、vGPU 管理组件和硬件指标 Exporter 的安装入口，并通过 GitHub Container Registry（GHCR）分发 OCI Helm Chart 和部分应用镜像。

## 厂商产物与安装入口

使用 Dynamia Chart 时，向 Helm 传入表中的 OCI 地址和 `--version`。海光 HCU Device Plugin、HCU Exporter 和燧原 GCU Exporter 的 Chart 发布前，可运行 `make chart` 打包，再按组件说明安装本地包。

| 厂商 | 组件 | 官方镜像或安装入口 | Dynamia OCI Helm Chart | Dynamia 应用镜像 |
| --- | --- | --- | --- | --- |
| 海光 HCU | [Device Plugin](vendors/hygon/hcu-device-plugin/README.md) | `harbor.sourcefind.cn:5443/hcu/admin/base/hcu-device-plugin:v3.0.2` 或 [v3.0.2 官方镜像包](https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/download/v3.0.2/hcu-device-plugin-v3.0.2.tar) | 版本 `3.0.2`<br>普通或 vHCU：`oci://ghcr.io/dynamia-ai/hygon/charts/k8s-hcu-plugin`<br>HAMi：`oci://ghcr.io/dynamia-ai/hygon/charts/k8s-hcu-plugin-hami`<br>MIG：`oci://ghcr.io/dynamia-ai/hygon/charts/k8s-hcu-plugin-mig` | `ghcr.io/dynamia-ai/hygon/hcu-device-plugin:v3.0.2` |
| 海光 HCU | [Exporter](vendors/hygon/hcu-exporter/README.md) | `harbor.sourcefind.cn:5443/hcu/admin/base/hcu-exporter:v3.0.2` 或 [v3.0.2 官方镜像包](https://github.com/HYGON-AI/hcu-exporter/releases/download/v3.0.2/hcu-exporter-v3.0.2.tar) | `oci://ghcr.io/dynamia-ai/hygon/charts/hcu-exporter-charts`，版本 `3.0.2` | `ghcr.io/dynamia-ai/hygon/hcu-exporter:v3.0.2` |
| 华为昇腾 | [NPU Exporter](vendors/ascend/npu-exporter/README.md) | `swr.cn-south-1.myhuaweicloud.com/ascendhub/npu-exporter:v26.2.0-openeuler24.03` | `oci://ghcr.io/dynamia-ai/ascend/charts/npu-exporter`，版本 `26.2.0` | — |
| 天数智芯 | [IX Device Plugin](vendors/iluvatar/ix-device-plugin/README.md) | `registry.iluvatar.com.cn:10443/k8s/ix-device-plugin:4.3.0` | `oci://ghcr.io/dynamia-ai/iluvatar/charts/ix-device-plugin`，版本 `4.3.0` | — |
| 天数智芯 | [IX Exporter](vendors/iluvatar/ix-exporter/README.md) | `registry.iluvatar.com.cn:10443/k8s/ix-exporter:4.3.0` | `oci://ghcr.io/dynamia-ai/iluvatar/charts/ix-exporter`，版本 `4.3.0` | — |
| 天数智芯 | [Iluvatar vGPU Manager](vendors/iluvatar/vgpu-manager/README.md) | `registry.iluvatar.com.cn:10443/cloud/gpu-manager:v3.0.10-vcuda-v5.0.1-r1` | `oci://ghcr.io/dynamia-ai/iluvatar/charts/iluvatar-vgpu-manager`，版本 `3.0.10` | — |
| AMD | [Device Metrics Exporter](vendors/amd/device-metrics-exporter/README.md) | `docker.io/rocm/device-metrics-exporter:v1.5.3`。驱动检查容器使用 `docker.io/library/busybox:1.36`。 | `oci://ghcr.io/dynamia-ai/amd/charts/device-metrics-exporter-charts`，版本 `1.5.3` | — |
| 燧原 GCU | [GCU Exporter](vendors/enflame/gcu-exporter/README.md) | 官方清单引用 `artifact.enflame.cn/enflame_docker_images/enflame/gcu-exporter:latest`，GCU Operator 用同一仓库的 `default` 标签。使用厂商镜像前请检查集群能否访问仓库。 | `oci://ghcr.io/dynamia-ai/enflame/charts/gcu-exporter-charts`，版本 `3.6.5` | `ghcr.io/dynamia-ai/enflame/gcu-exporter:v3.6.5`（`linux/amd64`） · [对应源码](vendors/enflame/gcu-exporter/SOURCES.md) |
| 燧原 GCU | [Device Plugin](vendors/enflame/README.md) | 官方 Chart 默认使用 `artifact.enflame.cn/enflame_docker_images/enflame/k8s-device-plugin:v2.0.0`。若集群无法访问仓库，按官方指南构建镜像。 | — | — |
| 沐曦 GPU | [MX Exporter](vendors/metax/mx-exporter/README.md) | `cr.metax-tech.com/cloud/mx-exporter`。获取拉取权限后按架构选用标签，也可从[沐曦软件中心](https://developer.metax-tech.com/softnova)获取离线包。 | `oci://ghcr.io/dynamia-ai/metax/charts/mx-exporter`，版本 `0.15.2` | — |
| 沐曦 GPU | [Device Plugin](vendors/metax/README.md) | `cr.metax-tech.com/cloud/gpu-device`。通过 [GPU Operator](https://developer.metax-tech.com/api/client/document/preview/1411/k8s/02_start.html) 安装，访问仓库需授权。 | — | — |
| 摩尔线程 | [MT GPU Exporter](vendors/mthreads/mtgpu-exporter/README.md) | KUAE `v2.1.0` 使用 `registry.mthreads.com/mcconline/mtgpu-exporter:2.1.0`。KUAE `v2.2.0` 改用 MT DCGM Exporter，镜像引用见套件内的 `dcgm-and-exporter.yaml`，公网镜像命名空间为 `registry.mthreads.com/mcconline`。 | — | `ghcr.io/dynamia-ai/mthreads/mtgpu-exporter:v2.1.0` |
| 昆仑芯 XPU | [DCXM Exporter](vendors/kunlunxin/README.md#dcxm-exporter-离线安装) | 下载 [1.0.0.1 官方离线包](https://klx-sdk-release-public.su.bcebos.com/xre/component/dcxm-exporter/1.0.0.1/dcxm-exporter-ubuntu20.04_1.0.0.1.tar.gz)，导入镜像后运行容器。 | — | — |
| 昆仑芯 XPU | [TKE XPU 组件](vendors/kunlunxin/README.md#腾讯云-tke-安装入口) | 在 TKE 组件管理安装 `xpu-gpu`，默认镜像仓库为 `ccr.ccs.tencentyun.com`。 [TKE 组件说明](https://cloud.tencent.com/document/product/457/138230) | — | — |
| 寒武纪 MLU | [Device Plugin 与 MLU Exporter](vendors/cambricon/README.md) | 两个组件的 `v2.5.0` 源码均提供独立 Chart。使用配套驱动包构建镜像，再将镜像仓库和标签传给 Chart。 | — | — |

## 本地构建

准备 Python 3.15、GNU Make 和 Bash 4 或更高版本。应用镜像配方需要 Skopeo，Chart 配方需要 Helm 和 Mike Farah 的 yq。构建燧原 GCU Exporter 镜像还需要 Docker Buildx。

```bash
make -C vendors/hygon/hcu-exporter app
make -C vendors/hygon/hcu-exporter chart
```

默认将产物写入各组件的 `dist/`。

## 运行公开检查

安装 uv 后，在仓库根目录检查组件和仓库工具。运行 `build` 时，将 `hygon/hcu-exporter` 替换为要检查的组件。

```bash
uv run --locked python scripts/components.py matrix
uv run --locked python scripts/components.py build hygon/hcu-exporter
uv run --locked ruff check scripts tests
uv run --locked ruff format --check scripts tests
uv run --locked python -m unittest discover -s tests
bash -n scripts/import-image.sh
```

[目录约定与厂商接入计划](docs/accelerator-artifacts-design.md) · [发布操作](docs/operations.md) · [贡献规则](CONTRIBUTING.md)
