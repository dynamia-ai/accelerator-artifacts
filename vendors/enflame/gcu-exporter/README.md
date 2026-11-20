# 燧原 GCU Exporter

`make app` 复用 EnflameTechnology 的 `v3.6.5` 源码和编译入口，在本地生成 `dist/gcu-exporter/image-source`。源码固定到提交 `a83264c908916e94480a42cddcd0615c56def9e6`，构建时校验归档 SHA-256。使用 Docker Buildx 和 Skopeo，在原生 `linux/amd64` 或 `linux/arm64` 环境中每次生成一个平台的 OCI 镜像。编译使用归档自带的 Go 依赖、EFML 绑定和头文件，并保留 EFML 函数符号供运行时解析。 [官方 Release](https://github.com/EnflameTechnology/gcu-exporter/releases/tag/v3.6.5) · [上游 Makefile](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/Makefile)

当前 GitHub Actions 的构建检查和发布任务均使用 `ubuntu-24.04` runner，工作流仅面向 `linux/amd64` 镜像。`linux/arm64` 镜像已在本地原生环境完成构建验证。 [构建检查](../../../.github/workflows/public-checks.yml) · [发布工作流](../../../.github/workflows/release.yml) · [GitHub 托管运行器架构](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

组件版本检查测试需单独执行。在仓库根目录运行以下命令。

```bash
python3 -m unittest discover -s vendors/enflame/gcu-exporter
```

官方 Release 提供源码归档。Exporter 部署示例和 GCU Operator 分别引用厂商仓库的 `latest` 和 `default`。匿名 Skopeo 查询均在仓库域名解析阶段失败，成品的固定版本、digest 和镜像架构待厂商确认。Exporter 的 x86 和 ARM 部署示例使用同一镜像引用。 [Exporter 部署说明](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/deployments/README.md) · [Operator DaemonSet](https://github.com/EnflameTechnology/k8s-operator/blob/073e86d77c8a288d198117a6049755145acc23ce/enflame-resources/gcu-exporter/gcu-exporter-ds.yaml)

## 部署到 Kubernetes

在节点上安装配套 GCU 驱动。按节点架构选择厂商的 DaemonSet 清单，将容器镜像替换为集群可拉取的同架构镜像。 [x86 清单](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/deployments/yaml/gcu-exporter.yaml) · [ARM 清单](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/deployments/yaml/gcu-exporter-for-arm.yaml)

如果 ARM64 节点的库文件是 `/usr/lib/libefml-arm.so`，在 ARM 清单中保留 `libefml` 卷的 `hostPath.path` 为 `/usr/lib/libefml-arm.so`，并将同名 `volumeMounts` 项的容器 `mountPath` 改为 `/usr/lib/libefml.so`。保留 `libefml-real` 卷从宿主机 `/usr/local/efsmi` 到容器 `/usr/local/efsmi` 的挂载。Exporter 在解析命令行参数前查找 `libefml.so` 或带版本号的库名。启动时如遇 EFML 符号查找错误，检查库的挂载路径及其依赖。 [EFML 加载逻辑](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/vendor/go-eflib/efml/efml_dl.go)

### 混合架构集群

上游两份清单的 DaemonSet 同名、使用相同的 Pod 标签和选择器，且均缺少架构 `nodeSelector`。在同时包含 `amd64` 和 `arm64` 节点的集群中，按下表分别修改两份清单，使两个 DaemonSet 只选择各自架构的节点和 Pod。 [Kubernetes DaemonSet 文档](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)

| 字段 | x86 清单 | ARM 清单 |
| --- | --- | --- |
| DaemonSet `metadata.name` | `gcu-exporter-amd64` | `gcu-exporter-arm64` |
| DaemonSet `spec.selector.matchLabels.name` 和 `spec.template.metadata.labels.name` | `gcu-exporter-amd64` | `gcu-exporter-arm64` |
| Pod `nodeSelector` 的 `kubernetes.io/arch` | `amd64` | `arm64` |
| Exporter 容器镜像 | 集群可拉取的 `linux/amd64` 镜像 | 集群可拉取的 `linux/arm64` 镜像 |

如果沿用两份清单附带的 Service，分别将其命名为 `gcu-exporter-amd64-service` 和 `gcu-exporter-arm64-service`，并将各自的 `spec.selector.name` 改为对应的 Pod 标签值。Prometheus 使用 TCP `9400` 的 `/metrics` 端点。

公开发布状态及需要随镜像交付的许可材料见[分发说明](#分发说明)。

## 分发说明

自建镜像随附上游声明，并提供与构建输入对应的源码包。 [上游许可证原文](LICENSE) · [源码交付说明](SOURCES.md)

`gcu-exporter` 源码和源码归档内的 `go-eflib` 绑定采用 Apache License 2.0。按适用许可证履行义务后，可以再分发受该许可覆盖的源码和编译产物。镜像在 `/usr/share/doc/gcu-exporter/` 保留上游 `LICENSE`、`LICENSE.md`、`NOTICE`、Go 许可和源码归档中的第三方许可文件。`go-eflib` 绑定编译进 Exporter，EFML 运行库由节点的厂商驱动提供。 [上游许可证](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/LICENSE) · [上游 NOTICE](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/NOTICE) · [go-eflib 许可证](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/vendor/go-eflib/LICENSE)

- **本仓库构建的 OCI 镜像**通过 GitHub Release 提供固定的 Exporter 源码归档、Debian 基础镜像内的对应源码包及构建配方。镜像标签和 OCI 许可附件都指向该 Release。
- **厂商成品镜像**待厂商确认。官方公开源码的许可证覆盖源码及其衍生作品，成品里的基础镜像、第三方软件和随包运行库各有条款。取得固定镜像及其内容清单后，按镜像核对再分发授权和交付义务。 [厂商镜像配置](https://github.com/EnflameTechnology/gcu-exporter/blob/a83264c908916e94480a42cddcd0615c56def9e6/deployments/build-image.conf)
