# AMD Device Metrics Exporter

本组件使用 ROCm `v1.5.3` 的官方 GPU Exporter 镜像和独立 Helm Chart。AMD Device Plugin 沿用 HAMi 社区版本。 [ROCm Release](https://github.com/ROCm/device-metrics-exporter/releases/tag/v1.5.3) · [制品分发状态](#分发说明)

## 从 AMD 官方 Helm 仓库安装

- Kubernetes 1.29.0 或更高版本、Helm 3.2.0 或更高版本，以及可访问集群的 `kubectl`。GPU 节点使用 `linux/amd64`。宿主机系统按 AMD 指南使用 Ubuntu 22.04 或更高版本，或 SUSE Linux Enterprise Server 15、16。 [AMD Helm 安装说明](https://github.com/ROCm/device-metrics-exporter/blob/v1.5.3/docs/installation/kubernetes-helm.md)
- 宿主机须加载 AMDGPU 驱动。MI2xx、MI3xx 使用 ROCm 6.2 或更高版本，MI350P、Radeon AI 使用 ROCm 7.13 或更高版本。 [v1.5.3 硬件支持](https://github.com/ROCm/device-metrics-exporter/releases/tag/v1.5.3)
- DaemonSet 的 init 容器和 Exporter 容器均以特权模式运行，需要允许宿主机路径挂载。init 容器从宿主机 `/sys` 检查 KFD 和 AMDGPU 驱动。Exporter 挂载 `/dev`、`/sys` 和 kubelet 的 PodResources 目录。如 kubelet 使用非默认目录，设置 `kubelet.podResourceAPISocketPath`。 [上游 DaemonSet 模板](https://github.com/ROCm/device-metrics-exporter/blob/v1.5.3/helm-charts/templates/daemonsets.yaml)

异构集群按以下示例创建 `amd-gpu-values.yaml`，同时匹配 AMD GPU 节点标签和 `amd64` 架构。将 `example.com/accelerator` 及其值替换为集群实际使用的 AMD GPU 节点标签。若目标节点有 `NoSchedule` 或 `NoExecute` 污点，按实际的污点键、值和 effect 配置对应的 `tolerations`。目标节点没有需要容忍的污点时可省略 `tolerations`。

```yaml
nodeSelector:
  kubernetes.io/arch: amd64
  example.com/accelerator: amd-gpu
tolerations:
  - key: example.com/accelerator
    operator: Equal
    value: amd-gpu
    effect: NoSchedule
```

```bash
helm repo add rocm-exporter https://rocm.github.io/device-metrics-exporter
helm repo update
helm install exporter rocm-exporter/device-metrics-exporter-charts \
  --version v1.5.3 --namespace kube-amd-gpu --create-namespace \
  -f amd-gpu-values.yaml
```

如果集群的所有节点都符合部署条件，可省略 `-f amd-gpu-values.yaml`。

默认从 Docker Hub 拉取 `docker.io/rocm/device-metrics-exporter:v1.5.3` 和驱动检查容器 `docker.io/library/busybox:1.36`。如需使用已获准的镜像仓库，分别通过 `image.repository`、`image.tag` 和 `image.initContainerImage` 覆盖。 [上游 Chart 默认值](https://github.com/ROCm/device-metrics-exporter/blob/v1.5.3/helm-charts/values.yaml)

## 检查指标

默认 ClusterIP Service 使用 TCP 5000 和 `internalTrafficPolicy: Local`。集群内经 ClusterIP 访问时，流量只发往来源节点上的就绪端点。先检查 Exporter Pod 的就绪状态，再通过端口转发访问 Service 选中的一个 Pod。端口转发绕过 ClusterIP 的节点本地转发。 [Kubernetes Service 内部流量策略](https://kubernetes.io/docs/concepts/services-networking/service-traffic-policy/) · [kubectl port-forward](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/)

```bash
kubectl -n kube-amd-gpu get pods -l app.kubernetes.io/name=metrics-exporter -o wide
kubectl -n kube-amd-gpu port-forward service/exporter-amd-metrics-exporter-svc 5000:5000
```

保持端口转发运行，在另一个终端访问指标端点。

```bash
curl -fsS http://127.0.0.1:5000/metrics
```

启用 `serviceMonitor.enabled` 前需要安装 Prometheus Operator 的 ServiceMonitor CRD。 [AMD Helm 安装及验证](https://instinct.docs.amd.com/projects/device-metrics-exporter/en/latest/installation/kubernetes-helm.html)

## 准备本地产物

在本目录运行 `make app` 按固定 digest 读取 Docker Hub 镜像，校验其 digest 和 `linux/amd64` 平台，并生成 `dist/device-metrics-exporter/image-source`。运行 `make chart` 下载并验证 AMD 官方 Chart，生成 `dist/device-metrics-exporter-charts/device-metrics-exporter-charts-1.5.3.tgz`。打包后的 Chart 仍从 Docker Hub 拉取上述两个镜像。

更新组件版本时，用 Skopeo 核对新版本的官方 tag、manifest digest 和平台。在本页的分发说明中记录对应的 digest 和平台，更新上游 `LICENSE`、`component.toml` 的版本以及 Makefile 中的 `APP_VERSION` 和 `APP_DIGEST`。日常构建直接读取已记录的 digest。

## 分发说明

Chart 和镜像均待发布审批。 [上游许可证原文](LICENSE)

### Helm Chart

`device-metrics-exporter-charts` 的分发依据为 ROCm 上游 Apache License 2.0。输入为 AMD Helm 仓库的 `device-metrics-exporter-charts-v1.5.3.tgz`，SHA-256 为 `c653e9918a1f1d4d2021e775d3e2b3c953d686fcffd55f865e7562f5b76a7634`。核对范围包括归档内的 Chart 元数据、模板、默认值和配置。归档的 `config.json` 与上游 `v1.5.3` 打包规则从 `example/config-gpu.json` 生成的文件一致。官方包无 Helm 子 Chart 和 `NOTICE` 文件。 [官方 Chart 索引](https://rocm.github.io/device-metrics-exporter/index.yaml) · [Chart 发布提交](https://github.com/ROCm/device-metrics-exporter/commit/19be53b32d50357078afe22b06c410b2baa62b8a) · [上游许可证](https://github.com/ROCm/device-metrics-exporter/blob/v1.5.3/LICENSE)

Dynamia 将 `Chart.yaml` 的 `version` 从 `v1.5.3` 改为 `1.5.3` 以符合 OCI 打包约定，并在同一文件的 `dynamia.ai/redistribution-changes` annotation 记录修改者和改动。包内保留上游 `appVersion`、适用版权声明和其他上游文件，并附上与上游许可证逐字节一致的 `LICENSE`。Chart 引用 ROCm Exporter 和 BusyBox 镜像，集群从 Docker Hub 拉取镜像。

### GPU Exporter 镜像

首次锁定时，Skopeo 读取到 AMD 官方 tag `docker.io/rocm/device-metrics-exporter:v1.5.3` 对应单平台 `linux/amd64` 镜像，manifest digest 为 `sha256:bdfc644bb8d4d07d9a0c31dda3e0d463101f48170548c5a7e7f7066c253fa813`。审核范围为该 digest 的完整镜像，包含底层保留的文件。镜像公开再分发待审核。 [AMD Docker Hub](https://hub.docker.com/r/rocm/device-metrics-exporter/tags)

- 镜像附带的 `/licenses/LICENSE` 与 Exporter 上游 Apache-2.0 文本一致。上游构建配方使用的 GPU Agent 源码也采用 Apache-2.0。镜像标注的构建修订 `f354e3d450169972cb1f8df64acae506d96d4c49` 在公开 Exporter 仓库无法解析，正式源码标签指向 `3b3c7f0bd5c0ec0bf00b9960d1b736258b7190eb`。 [Exporter 源码许可](https://github.com/ROCm/device-metrics-exporter/blob/v1.5.3/LICENSE) · [GPU Agent 源码许可](https://github.com/ROCm/gpu-agent/blob/bcae57f9b395363f3340ad0b7393659b7df13f37/LICENSE)
- 镜像层包含 Red Hat UBI 9 Minimal 9.8、额外安装的 RPM、GPU Agent、ROCm 10.1.0 库和第三方库。抽查确认了 AMD SMI 27.1.0、HIP、HSA Runtime、AQLprofile、ROCprofiler-SDK、rocRAND、ROCm 打包的 MPFR，以及较早层中的 AMD SMI 26.5.0。镜像内可见 AMD SMI 的 MIT 许可和 MPFR 的 GPL、LGPL 文本。RPM 数据库也记录了 Bash 的 GPL 许可及其源码 RPM 名称。 [ROCm 10.1.0 组件许可](https://rocm.docs.amd.com/en/docs-10.1.0/about/license.html) · [Red Hat UBI 分发条款说明](https://developers.redhat.com/articles/ubi-faq)
- 公开镜像发布需补齐与此 digest 对应的组件、源码及许可清单，核对额外 RPM 的 UBI 来源，确认各层的第三方声明、对应源码和其他交付义务。当前清单中的 Chart 和镜像均待审核，组件发布检查会拦截此版本。
