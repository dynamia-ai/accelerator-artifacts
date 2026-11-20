# 沐曦 mx-exporter

`make chart` 将 MetaX-MACA 的独立 Helm Chart 打包为 `dist/mx-exporter/mx-exporter-0.15.2.tgz`。Chart 默认引用 `cr.metax-tech.com/cloud/mx-exporter:0.15.2`。上游也提供原生 Kubernetes YAML。 [上游 Helm Chart 和 YAML](https://github.com/MetaX-MACA/mxExporter/tree/99fc48a1c1509e7fc7eefac8d334a7f0547adb0b/deployment/mx-exporter) · [沐曦 0.15.2 集群监控部署手册](https://developer.metax-tech.com/api/client/document/preview/1275/split_files/mx_exporter%E9%83%A8%E7%BD%B2.html)

## 获取镜像

通过沐曦获取 `cr.metax-tech.com` 的拉取权限，或从沐曦软件中心获取配套的离线镜像包。Red Hat 认证目录列出 `0.15.2-amd64` 和 `0.15.2-arm64`，均关联 `0.15.2`。匿名查询这三个标签的镜像清单均返回 `authentication required`。无架构后缀的 `0.15.2` 标签及其平台支持仍待核实。无论是单架构还是混合架构集群，使用该标签前都需确认镜像可拉取，并支持所有目标节点的架构。使用离线镜像时，按节点架构选择归档。 [沐曦软件中心](https://developer.metax-tech.com/softnova) · [官方软件包获取说明](https://developer.metax-tech.com/api/client/document/preview/1411/k8s/02_start.html) · [Red Hat 认证镜像目录](https://catalog.redhat.com/en/software/containers/cloud/mx-exporter/698361e0800f86b3c437e8ac)

## 安装独立 Chart

按沐曦手册准备 GPU 节点和驱动。Chart 使用特权容器，并挂载宿主机的 `/dev/dri` 和 kubelet Pod Resources 目录。从仓库根目录进入组件目录并打包 Chart。

```bash
cd vendors/metax/mx-exporter
make chart
```

使用架构专用镜像时，必须用 `nodeSelector.kubernetes\.io/arch` 将 DaemonSet 限制在对应架构的节点。若同一架构还有非 GPU 节点，在 `nodeSelector` 中同时加入目标集群已有的 GPU 节点标签及其值。 [Kubernetes 节点架构标签](https://kubernetes.io/docs/reference/labels-annotations-taints/#kubernetes-io-arch)

单架构集群执行对应架构的安装命令。混合架构集群使用两种架构专用镜像时，将 amd64 和 arm64 分别装到 `metax-monitor-amd64` 和 `metax-monitor-arm64`。Chart 在每个命名空间创建固定名称的 `exporter-metrics-config-map`，两个 release 需要各自的命名空间。

将对应架构的 `*_IMAGE_REPOSITORY` 和 `*_IMAGE_TAG` 环境变量设为已核实的镜像仓库和标签。使用离线包时，填写导入后实际供集群拉取的仓库和标签。若仓库需要认证，先创建每个安装命名空间，并在各自的命名空间中准备对应凭据的拉取 Secret。将命令中的 `metax-registry` 替换成该命名空间中的 Secret 名称。若仓库允许匿名拉取，省略 `imagePullSecrets` 参数，由 `--create-namespace` 创建命名空间。

### amd64

```bash
helm install metax-mx-exporter ./dist/mx-exporter/mx-exporter-0.15.2.tgz \
  --namespace metax-monitor-amd64 --create-namespace \
  --set 'imagePullSecrets[0].name=metax-registry' \
  --set-string 'nodeSelector.kubernetes\.io/arch=amd64' \
  --set-string "image.repository=${MX_EXPORTER_AMD64_IMAGE_REPOSITORY:?}" \
  --set-string "image.tag=${MX_EXPORTER_AMD64_IMAGE_TAG:?}"
```

### arm64

```bash
helm install metax-mx-exporter ./dist/mx-exporter/mx-exporter-0.15.2.tgz \
  --namespace metax-monitor-arm64 --create-namespace \
  --set 'imagePullSecrets[0].name=metax-registry' \
  --set-string 'nodeSelector.kubernetes\.io/arch=arm64' \
  --set-string "image.repository=${MX_EXPORTER_ARM64_IMAGE_REPOSITORY:?}" \
  --set-string "image.tag=${MX_EXPORTER_ARM64_IMAGE_TAG:?}"
```

## 配置 Prometheus 抓取

在 Prometheus 中配置 Kubernetes 服务发现，选择各安装命名空间中 `metax-mx-exporter` Service 的端点。抓取每个 Exporter Pod 在 `8000` 端口暴露的 `/metrics`。如果 GPU Operator 已在目标节点部署 `mx-exporter`，沿用 Operator 的监控配置。 [Prometheus Kubernetes 服务发现](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config) · [沐曦集群监控部署手册](https://developer.metax-tech.com/api/client/document/preview/1275/split_files/mx_exporter%E9%83%A8%E7%BD%B2.html) · [GPU Operator 安装手册](https://developer.metax-tech.com/api/client/document/preview/1411/k8s/02_start.html) · [分发说明](#分发说明)

## 分发说明

当前清单只登记 OCI Helm Chart。发布后可将安装命令中的本地归档替换为 `oci://ghcr.io/dynamia-ai/metax/charts/mx-exporter`，并指定 `--version 0.15.2`。安装时仍需传入已核实的厂商镜像仓库和标签。 [上游许可证原文](LICENSE)

### Helm Chart 0.15.2

打包输入为 `MetaX-MACA/mxExporter` 提交 `99fc48a1c1509e7fc7eefac8d334a7f0547adb0b` 下的独立 Helm Chart。上游仓库的 `LICENSE` 标题为 `BSD 3.0 LICENSE`，正文允许按所列条件再分发。包内保留原文、版权声明、条件和免责声明。 [固定版本 Chart 源码](https://github.com/MetaX-MACA/mxExporter/tree/99fc48a1c1509e7fc7eefac8d334a7f0547adb0b/deployment/mx-exporter/helm/mx-exporter) · [上游 LICENSE](https://github.com/MetaX-MACA/mxExporter/blob/99fc48a1c1509e7fc7eefac8d334a7f0547adb0b/LICENSE)

上游 Chart 声明 `version: 0.8.1`、`appVersion: 2.2.11` 和默认镜像标签 `latest`。本仓库将包版本、`appVersion` 和默认镜像标签统一为厂商镜像版本 `0.15.2`。包内包含部署模板和配置，镜像由集群直接从沐曦或获授权的镜像仓库拉取。 [沐曦 0.15.2 部署手册](https://developer.metax-tech.com/api/client/document/preview/1275/split_files/mx_exporter%E9%83%A8%E7%BD%B2.html)

### 镜像和 MXMACA 依赖

厂商镜像 `0.15.2` 的公开再分发待确认。上游 Dockerfile 会将 `dep/` 和应用代码复制到镜像中。固定提交中的 `dep/libmxsml.so` 是 Linux x86-64 动态库，`dep/mxsmlBindings.py` 和 `mx_exporter/mx_exporter.py` 含要求沐曦事先书面许可的专有声明。MXMACA SDK 安装也要求接受独立的 EULA，目前缺少覆盖该二进制库、相关代码及整张镜像的公开再分发授权。镜像层和实际依赖清单须在取得仓库权限后核验。 [上游 Dockerfile](https://github.com/MetaX-MACA/mxExporter/blob/99fc48a1c1509e7fc7eefac8d334a7f0547adb0b/Dockerfile) · [MXSML 依赖目录](https://github.com/MetaX-MACA/mxExporter/tree/99fc48a1c1509e7fc7eefac8d334a7f0547adb0b/dep) · [Exporter 源码声明](https://github.com/MetaX-MACA/mxExporter/blob/99fc48a1c1509e7fc7eefac8d334a7f0547adb0b/mx_exporter/mx_exporter.py#L4-L27) · [MXMACA SDK 安装与 EULA](https://developer.metax-tech.com/api/client/document/preview/%E5%AE%89%E8%A3%85%E6%8C%87%E5%8D%97/%E5%BF%AB%E9%80%9F%E4%B8%8A%E6%89%8B%E6%8C%87%E5%8D%97/MXC500/3.9.1/split_files/%E7%BC%96%E7%A8%8B%E7%8E%AF%E5%A2%83.html)
