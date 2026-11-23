# 独立 IX Device Plugin

IX Device Plugin 通过 kubelet 将 GPU 注册为 `iluvatar.com/gpu`。应用在容器的 `resources.limits` 中声明所需数量。厂商还提供板卡拆分和时间片共享配置。需要 HAMi 按卡型申请 vGPU、显存和算力时，使用 [Iluvatar vGPU Manager](../vgpu-manager/README.md)。 [上游使用说明](https://github.com/Deep-Spark/ix-device-plugin/blob/v4.3.0/README.md)

先按厂商要求在目标节点安装驱动和 CoreX 软件栈。从 DeepSpark Release 下载 `ix-device-plugin-4.3.0.tgz`。该附件内的 Chart 版本为 `4.3.0`，默认从 `registry.iluvatar.com.cn:10443/k8s/ix-device-plugin:4.3.0` 拉取镜像。该标签的索引包含 Linux amd64 和 arm64，镜像配置的 `version` 标签在 amd64 上为 `4.3.0`，在 arm64 上为 `4.3.6`。 [DeepSpark v4.3.0 Release](https://github.com/Deep-Spark/ix-device-plugin/releases/tag/v4.3.0) · [镜像索引与许可记录](#运行镜像)

上游 Chart 默认启用 `ixConfig.flags.splitboard`。需要按整块板卡注册时，设置 `ixConfig.flags.splitboard=false`。在混合节点集群中，通过 `nodeSelector` 或 `affinity` 选择天数智芯 GPU 节点。

```bash
helm upgrade --install ix-device-plugin ./ix-device-plugin-4.3.0.tgz \
  --namespace kube-system \
  --set ixConfig.flags.splitboard=false
kubectl -n kube-system rollout status daemonset/ix-device-plugin
```

安装后，通过 `kubectl describe node` 在目标 GPU 节点的 `Allocatable` 中检查 `iluvatar.com/gpu`。本目录的 `make chart` 重新打包官方 Chart 并补齐许可。`make app` 输出 `device-plugin/image-source`，指向固定的双架构镜像索引。 [再分发记录](#分发说明)

## 分发说明

Chart 可按产物单独发布。运行镜像继续使用厂商来源。 [上游许可证原文](LICENSE)

### Helm Chart

公开再分发依据为 Apache License 2.0。官方 Release 附件的模板与提交 `4c93f150348d97e4d647f7c3b0e0a450ba73c18d` 中的模板一致，附件采用发布用的 Chart 名称和版本，并将默认镜像仓库指向天数智芯。重新打包时保留官方包的模板和值，随包附带上游 `LICENSE`。 [上游 Release](https://github.com/Deep-Spark/ix-device-plugin/releases/tag/v4.3.0) · [Chart 源码](https://github.com/Deep-Spark/ix-device-plugin/tree/4c93f150348d97e4d647f7c3b0e0a450ba73c18d/deployment/ix-device-plugin) · [上游许可证](https://github.com/Deep-Spark/ix-device-plugin/blob/4c93f150348d97e4d647f7c3b0e0a450ba73c18d/LICENSE)

### 运行镜像

公开再分发待审核。厂商标签 `4.3.0` 指向包含 Linux amd64 和 arm64 的索引 `sha256:5b60c3a70173bc093592ab195daedb84a9e8b6e5a576d40997f608761e3dafc2`。amd64 和 arm64 配置中的 `version` 分别为 `4.3.0` 和 `4.3.6`。两种架构的镜像层均包含 `/usr/local/corex/lib64` 中的 `libixml`、`libcuda` 和 `libcudart`。核对范围包括官方 Release、上游 Dockerfile、两种架构的镜像配置和层文件列表。发布前需请厂商确认两个平台的实际成品版本，以及完整镜像、随镜像交付的 CoreX 库和第三方组件的公开镜像权限及声明义务。 [上游 Dockerfile](https://github.com/Deep-Spark/ix-device-plugin/blob/v4.3.0/docker/Dockerfile) · [天数智芯软件许可条款](https://iluvatar.com/compliance?id=xy-eula)

通过 `skopeo inspect --config` 从索引指向的 arm64 清单 `sha256:480564b20caba9e1a56609603128c2167818083f3ae8a036bca6371ad1d5a499` 读取到 `config.Labels.version=4.3.6`。
