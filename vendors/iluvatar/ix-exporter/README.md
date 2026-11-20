# IX Exporter

IX Exporter 在天数智芯 GPU 节点上运行 DaemonSet，默认通过端口 `32021` 提供 Prometheus 指标。安装前在 GPU 节点准备厂商要求的驱动和软件栈，并确认节点能访问厂商镜像仓库。Chart 要求 Kubernetes 1.16 或更新版本。 [上游部署说明](https://github.com/Deep-Spark/ix-exporter/tree/v4.3.0/deployment)

从 DeepSpark Release 下载 `ix-exporter-4.3.0.tgz`。Chart 默认使用厂商镜像 `registry.iluvatar.com.cn:10443/k8s/ix-exporter:4.3.0`。该标签的索引包含 Linux amd64 和 arm64，镜像配置的 `version` 标签在 amd64 上为 `4.3.0`，在 arm64 上为 `4.3.6`。附件内的 Chart 版本和 `appVersion` 均为 `1.0.0`，运行镜像由 Chart 的 `image` 值指定。 [DeepSpark v4.3.0 Release](https://github.com/Deep-Spark/ix-exporter/releases/tag/v4.3.0) · [镜像索引与许可记录](#运行镜像)

```bash
helm upgrade --install ix-exporter ./ix-exporter-4.3.0.tgz --namespace kube-system
kubectl -n kube-system rollout status daemonset/ix-exporter
```

混合节点集群可通过 `nodeSelector` 选择天数智芯 GPU 节点。官方 `v4.3.0` 附件固定生成一组 `tolerations`（`CriticalAddonsOnly`），为 Chart 的 `tolerations` 传入非空列表会生成重复的 YAML 键。使用此 Chart 时保留 `tolerations: []`。目标节点需要额外容忍时，向厂商获取修复后的 Chart。 [DaemonSet 模板](https://github.com/Deep-Spark/ix-exporter/blob/v4.3.0/deployment/helm/ix-exporter/templates/daemonset.yaml)

需要 Prometheus Operator 自动发现时，先安装 ServiceMonitor CRD，再设置 `serviceMonitor.enabled=true`。ServiceMonitor 默认创建在 `monitoring` 命名空间。

本目录的 `make chart` 校验官方附件并补齐许可，输出 `ix-exporter/ix-exporter-4.3.0.tgz`。重新打包后的 Chart 版本与 Release 版本一致，保留上游模板和默认镜像。`make app` 输出 `exporter/image-source`，指向固定的双架构镜像索引。 [再分发记录](#分发说明)

## 分发说明

Chart 已记录版本审批，组件发布仍待运行镜像审核。 [上游许可证原文](LICENSE)

### Helm Chart

公开再分发依据为 Apache License 2.0。官方 Release 附件中的 Helm 文件与源码提交 `bbca3b39eff9e4da2fbe1a2f5639fffe8062b509` 的 Chart 文件一致。附件仅包含 Helm 部署文件，运行镜像通过 `image` 值引用。重新打包时随附源码根目录的 `LICENSE`，并保留模板版权声明。Dynamia 将 `Chart.yaml` 的 `version` 从 `1.0.0` 调整为 `4.3.0`，在该文件的 annotation 标明变更，并保留 `appVersion` 和运行镜像设置。 [上游 Release](https://github.com/Deep-Spark/ix-exporter/releases/tag/v4.3.0) · [Chart 源码](https://github.com/Deep-Spark/ix-exporter/tree/bbca3b39eff9e4da2fbe1a2f5639fffe8062b509/deployment/helm/ix-exporter) · [上游许可证](https://github.com/Deep-Spark/ix-exporter/blob/bbca3b39eff9e4da2fbe1a2f5639fffe8062b509/LICENSE)

### 运行镜像

公开再分发待审核。厂商标签 `4.3.0` 指向包含 Linux amd64 和 arm64 的索引 `sha256:e2050e1f7b4213a5413294f7977db852a34d8b5924caaee9ec48c934fbaad40b`。amd64 和 arm64 配置中的 `version` 分别为 `4.3.0` 和 `4.3.6`。两种架构的镜像层均包含 `/usr/local/corex/lib64` 中的 `libixml`、`libixdcgm`、`libcuda` 和 `libcudart`。核对范围包括官方 Release、上游 Dockerfile、两种架构的镜像配置和层文件列表。发布前需请厂商确认两个平台的实际成品版本，以及完整镜像、随镜像交付的 CoreX 库和第三方组件的公开镜像权限及声明义务。 [上游 Dockerfile](https://github.com/Deep-Spark/ix-exporter/blob/v4.3.0/Dockerfile) · [天数智芯软件许可条款](https://iluvatar.com/compliance?id=xy-eula)

通过 `skopeo inspect --config` 从索引指向的 arm64 清单 `sha256:28f343cc98d3df035c0c3273581517b4cdc1a57365f36fdd06f40867453f2b2d` 读取到 `config.Labels.version=4.3.6`。
