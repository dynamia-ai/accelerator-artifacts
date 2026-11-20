# 摩尔线程 MT GPU Exporter

仍在运行 KUAE 云原生套件 v2.1.0 的集群可继续使用 MT GPU Exporter。KUAE v2.2.0 已下线 `mt-gpu-exporter`，监控改用 MT DCGM Exporter，完整版本为 `v1.1.7-3.3.6-3.4.2`。 [v2.1.0 发布说明](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/history_version/v2.1.0/releasenote/) · [v2.2.0 发布说明](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/releasenote/)

厂商镜像 `registry.mthreads.com/mcconline/mtgpu-exporter:2.1.0` 可匿名读取，索引 digest 为 `sha256:610c146c3caaeec4c32985b47b674d9f7a0644ba88ea1b7fd5eb4c704e5787a5`，包含 `linux/amd64` 和 `linux/arm64`。

## v2.1.0 部署入口

从开发者门户登录并下载 KUAE 云原生套件 v2.1.0。Core 模式使用包内 `GPU-Operator/gpu-operator-core/deployments.yaml` 同时部署 Device Plugin 和 `mtgpu-exporter`。按安装指南准备驱动和 MT Container Toolkit，并为目标 GPU 节点设置 `mthreads.com/gpu=enable` 标签。部署后从 `mt-gpu-operator` 命名空间中的 `mtgpu-exporter` 服务抓取 `9445/TCP` 的 `/metrics`。 [v2.1.0 下载页](https://developer.mthreads.com/resources/artifacts/sdk-arti-00002) · [v2.1.0 安装指南](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/history_version/v2.1.0/install_guide/#k8s集群部署device-plugin和mtgpu-exporter组件)

Full 模式的 `mt-gpu-operator-2.1.0.tgz` 和 `mt-gpu-operator-custom-resources-2.1.0.tgz` 用于安装 Operator 和自定义资源。官方公开文件清单未列出独立的 Exporter Chart，单独部署可从 Core 模式的清单核对 Exporter 的配置。下载页要求登录，随包清单和 Chart 的实际内容尚未核验。 [v2.1.0 安装包文件清单](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/history_version/v2.1.0/releasenote/#文件描述)

## KUAE v2.2.0 监控与 Device Plugin

GPU Operator 安装指南在 Core 模式的 DCGM 安装步骤中使用 `kubectl apply -f dcgm-and-exporter.yaml`，该步骤只给出文件名。v2.2.0 发布说明的安装包文件清单将该文件列为 `GPU-Operator/gpu-operator-full/dcgm-and-exporter.yaml`。本仓库尚未核验 v2.2.0 压缩包内的实际路径。 [GPU Operator 安装指南](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/install_guide/operator_install/) · [v2.2.0 发布说明](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/releasenote/)

解压 v2.2.0 套件后，从包含 `GPU-Operator` 的目录查找清单。

```bash
find GPU-Operator -type f -name 'dcgm-and-exporter.yaml'
```

按 Core 安装指南准备节点后，将查到的清单路径传给 `kubectl apply -f`。该清单部署 MT DCGM（`v1.1.7-3.3.6`）和 MT DCGM Exporter。Exporter 连接节点上的 `mt-dcgm` hostengine，并通过 `9400/TCP` 暴露 `/metrics`。 [GPU Operator 安装指南](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/install_guide/operator_install/) · [DCGM Exporter 使用指南](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/user_guide/exporter_guide/)

Device Plugin 通过厂商 MT GPU Operator 安装。v2.2.0 Core 模式使用套件中的 `deployments.yaml`，Full 模式使用包内 Operator 和自定义资源 Chart。 [MT GPU Operator 安装指南](https://docs.mthreads.com/cloud-native/cloud-native-doc-online/install_guide/operator_install/)

## 构建与分发

运行 `make app` 校验厂商镜像索引的 digest，在 `dist/mtgpu-exporter/` 生成 `image-source` 和厂商协议副本 `LICENSE`。发布使用 Skopeo 保真复制双架构镜像，再将协议作为 OCI 附件关联到镜像索引。 [协议副本](LICENSE) · [摩尔线程软件使用许可协议](https://developer.mthreads.com/privacy)

发布后，使用工作流摘要中的 LICENSE 引用运行 `oras pull <LICENSE 引用>` 下载协议。也可以通过 `oras discover --artifact-type application/vnd.dynamia.license.v1 ghcr.io/dynamia-ai/mthreads/mtgpu-exporter:v2.1.0` 查找附件。 [ORAS 附件下载说明](https://oras.land/docs/how_to_guides/supply_chain_artifacts/)
