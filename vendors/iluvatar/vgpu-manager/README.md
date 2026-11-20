# Iluvatar vGPU Manager

HAMi 使用天数智芯的 `gpu-manager` 在 GPU 节点提供虚拟化能力，由 HAMi 负责调度。工作负载按卡型请求 `iluvatar.ai/<card-type>-vgpu`、`iluvatar.ai/<card-type>.vMem` 和 `iluvatar.ai/<card-type>.vCore`。单容器请求一张 GPU 时可使用 vGPU 模式。按 `iluvatar.com/gpu` 申请设备的集群可使用 [独立 IX Device Plugin](../ix-device-plugin/README.md)。 [HAMi 天数智芯共享指南](https://project-hami.io/docs/userguide/iluvatar-device/enable-iluvatar-gpu-sharing)

向设备供应商确认卡型、驱动和 VCUDA 版本的组合。HAMi v2.11 指南要求驱动版本高于 3.1.0。这里核对的 DeepSpark Release 是 `v3.0.10-v5.0.1-r1`，附件为 `iluvatar-vgpu-manager-3.0.10.tgz`，其 manager 镜像引用是 `registry.iluvatar.com.cn:10443/cloud/gpu-manager:v3.0.10-vcuda-v5.0.1-r1`，支持 Linux amd64 和 arm64。 [DeepSpark Gitee Release](https://gitee.com/deep-spark/iluvatar-vgpu-manager/releases/tag/v3.0.10-v5.0.1-r1) · [该版本安装说明](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/v3.0.10-v5.0.1-r1/README_zh.md)

## 核对节点的 CRI socket

当 `manager.containerRuntimeEndpoint` 为空时，Chart 会向 manager 传入 K3s 的默认路径 `/run/k3s/containerd/containerd.sock`。安装前，从每台目标 GPU 节点的 kubelet 或 Kubernetes 发行版配置核对实际的容器运行时接口（CRI）socket。同一个 DaemonSet 的所有 Pod 共用一个 endpoint。用 `crictl info` 验证对应 socket 能访问 CRI。下例适用于 socket 位于 `/var/run/containerd/containerd.sock` 的普通 containerd 节点。 [厂商 endpoint 模板](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/v3.0.10-v5.0.1-r1/charts/iluvatar-vgpu-manager/templates/_helpers.tpl) · [Kubernetes containerd 说明](https://kubernetes.io/docs/setup/production-environment/container-runtimes/#containerd)

```bash
sudo crictl --runtime-endpoint unix:///var/run/containerd/containerd.sock info
```

为 `manager.containerRuntimeEndpoint` 填写容器内的 socket 文件路径。Chart 将主机的 `/var/run` 挂载到容器的 `/var/run`。下面的 Helm 命令把该路径作为 `--container-runtime-endpoint=/var/run/containerd/containerd.sock` 传入 manager。如果实际 socket 路径不在 Chart 已挂载的目录中，先向设备供应商确认挂载方式。 [DaemonSet 模板](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/v3.0.10-v5.0.1-r1/charts/iluvatar-vgpu-manager/templates/gpu-manager/daemonset.yaml)

## 与 HAMi 一起部署

在每台目标 GPU 节点设置 `iluvatar.com/gpu.present=true`。与 HAMi 配合时只部署 `gpu-manager`，关闭厂商的 admission 和自动节点发现。手工标记节点时可同时跳过该 Chart 随包的 Node Feature Discovery CRD 和垃圾回收 RBAC。

```bash
helm upgrade --install iluvatar-vgpu-manager ./iluvatar-vgpu-manager-3.0.10.tgz \
  --namespace iluvatar-vgpu-manager --create-namespace --skip-crds \
  --set admission.enabled=false,ixfd.enable=false,gc.enable=false \
  --set-string manager.containerRuntimeEndpoint=/var/run/containerd/containerd.sock
kubectl -n iluvatar-vgpu-manager rollout status daemonset/iluvatar-vgpu-manager-manager
```

## 核对卡型和资源名

根据设备供应商确认的卡型和软件栈，在部署前核对两边的 values。Manager 的 `manager.product` 生成 `gpu-config` ConfigMap 的卡型条目及显存、算力资源名。HAMi 的 `devices.iluvatar.configs` 定义调度器识别的卡型及资源名。使用 HAMi 自带调度器时，还要在 `devices.iluvatar.customresources` 填入对应的数量、显存和算力资源名。

| 默认配置 | 卡型 |
| --- | --- |
| Manager Chart `3.0.10` 的 `manager.product` | `BI-V100`、`BI-V150`、`BI-V150S`、`MR-V100` |
| HAMi `v2.11.0` 的 `devices.iluvatar.configs` 和 `customresources` | `BI-V100`、`BI-V150`、`MR-V100`、`MR-V50` |

使用 `BI-V150S` 时核对 HAMi 两份列表，使用 `MR-V50` 时核对 Manager 的 `manager.product`。覆盖这些列表时提供要保留的完整列表。设置 `devices.iluvatar.enabled=true` 后，按 HAMi 的工作负载示例核验实际分配。默认配置只反映该版本 Chart 的值，设备支持以厂商确认的组合和实机验证为准。 [Manager Chart values](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/v3.0.10-v5.0.1-r1/charts/iluvatar-vgpu-manager/values.yaml) · [HAMi v2.11.0 values](https://github.com/Project-HAMi/HAMi/blob/v2.11.0/charts/hami/values.yaml) · [HAMi 天数智芯共享指南](https://project-hami.io/docs/userguide/iluvatar-device/enable-iluvatar-gpu-sharing)

## 原包的可选组件

按本页的 HAMi 安装方式，集群只需拉取厂商仓库的 `gpu-manager` 镜像。官方 Chart 默认启用 `admission.enabled`，另会使用以下镜像。

- `registry.iluvatar.com.cn:10443/cloud/gpu-admission:v3.0.10-vcuda-v5.0.1-r1`
- `registry.iluvatar.com.cn:10443/ingress-nginx/kube-webhook-certgen:v1.4.1`
- `registry.cn-hangzhou.aliyuncs.com/google_containers/kube-scheduler`，默认取集群 Kubernetes 版本的 `vX.Y.Z` 部分作为标签，可通过 `admission.kubeScheduler.image.tag` 固定。

另外开启 `ixfd.enable` 时，还会引用厂商仓库的 `cloud/ix-feature-discovery:v0.1.0` 和 `nfd/node-feature-discovery:v0.18.3`。 [官方 Chart 与镜像清单](https://gitee.com/deep-spark/iluvatar-vgpu-manager/releases/tag/v3.0.10-v5.0.1-r1)

## 本地打包

本目录的 `make chart` 重新打包官方 Chart 并附带许可，保留上游默认值。`make app` 输出 `gpu-manager/image-source`，指向固定的双架构 manager 镜像索引。 [再分发记录](#分发说明)

## 分发说明

Chart 可按产物单独发布。运行镜像继续使用厂商来源。 [上游许可证原文](LICENSE)

### Helm Chart

天数智芯源码声明使用 Apache License 2.0。官方 Gitee Release `v3.0.10-v5.0.1-r1` 的 Chart 模板、默认值和 CRD 对应源码提交 `1a3573b46a074894add1aa1e27e1755d0356450e`，`Chart.yaml` 由 Helm 重新序列化。Helm 打包时移除厂商 `LICENSE` 开头的 UTF-8 BOM，归档保留全部许可文本、版权、衍生说明和第三方声明。Chart 随包附带 NFD 的许可证及逐文件归属。 [上游 Release](https://gitee.com/deep-spark/iluvatar-vgpu-manager/releases/tag/v3.0.10-v5.0.1-r1) · [Chart 源码](https://gitee.com/deep-spark/iluvatar-vgpu-manager/tree/1a3573b46a074894add1aa1e27e1755d0356450e/charts/iluvatar-vgpu-manager) · [厂商许可证](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/1a3573b46a074894add1aa1e27e1755d0356450e/LICENSE)

[NFD 逐文件归属](NFD-ATTRIBUTION.md) · [NFD 许可证](NFD-LICENSE)

### 运行镜像

公开再分发待审核。厂商的 `gpu-manager:v3.0.10-vcuda-v5.0.1-r1` 索引 `sha256:e89fc5d078e64c059b4f18e8347d4f671bf9416d17cd410881e836286cdd7375` 包含 Linux amd64 和 arm64。两种架构的镜像层均以官方 `iluvatar/vcuda:v5.0.1-r1` 对应架构的层作为底座。核对范围包括上游 Dockerfile、版本配置、两个索引及对应平台的层清单。发布前需请厂商确认整个 manager 镜像及 VCUDA 底座的公开镜像权限和声明义务。 [上游镜像配方](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/v3.0.10-v5.0.1-r1/docker/gpu-manager/Dockerfile) · [VCUDA 版本配置](https://gitee.com/deep-spark/iluvatar-vgpu-manager/blob/v3.0.10-v5.0.1-r1/version.mk) · [天数智芯软件许可条款](https://iluvatar.com/compliance?id=xy-eula)
