# 海光 HCU Exporter

`make chart` 打包海光 HCU Exporter `v3.0.2` 的独立 Chart。Release 附件提供 Docker 镜像包、二进制和 Kubernetes YAML，Chart 源码位于同版本的 `deployment/helm/hcu-exporter`。 [官方 Release](https://github.com/HYGON-AI/hcu-exporter/releases/tag/v3.0.2) · [固定版本 Chart 源码](https://github.com/HYGON-AI/hcu-exporter/tree/30cfbc1031957737731725ceddb663bc508d7c96/deployment/helm/hcu-exporter)

## 安装 Chart

在带有 `hygon.com/hcu=true` 标签的 Linux amd64 节点上安装配套驱动和 HyHAL，并准备宿主机目录 `/opt/hyhal`。Chart 使用特权 DaemonSet 和宿主机网络，挂载 `/dev`、`/etc/hostname`、`/etc/vdev` 和 `/opt/hyhal`。默认还挂载 `/var/lib/kubelet` 并创建可在集群范围内列出和监听 Pod 的 RBAC。由旧清单迁移到 Helm 前，按原安装方式移除旧资源，释放对象名称和节点的 `16080/TCP` 端口。 [官方 Kubernetes 部署要求](https://github.com/HYGON-AI/hcu-exporter/blob/30cfbc1031957737731725ceddb663bc508d7c96/README.md#kubernetes-部署)

从仓库根目录打包并安装。

```bash
make -C vendors/hygon/hcu-exporter chart
helm upgrade --install hcu-exporter \
	./vendors/hygon/hcu-exporter/dist/hcu-exporter-charts/hcu-exporter-charts-3.0.2.tgz \
	--namespace kube-system
```

默认镜像是现有的 `ghcr.io/dynamia-ai/hygon/hcu-exporter:v3.0.2`。使用厂商 Harbor 时，在安装命名空间准备拉取 Secret。将下面的配置保存为 `hygon-values.yaml`，在安装命令中追加 `-f hygon-values.yaml`。也可用相同配置项指定由官方离线包导入的镜像。

```yaml
hcuExporter:
  hcuExporter:
    image:
      repository: harbor.sourcefind.cn:5443/hcu/admin/base/hcu-exporter
      tag: v3.0.2
imagePullSecrets:
  - name: hygon-registry
```

Prometheus 可按 Pod 注解抓取 `http://<节点IP>:16080/metrics`。用 `hcuExporter.hcuExporter.env.hcuExporterListen` 修改监听端口时，Pod 端口和抓取注解会同步更新。Service 默认使用 NodePort，服务端口为 `16080`，并转发到 Pod 的命名端口 `metrics`。默认采集档位沿用官方 Chart 的 `high`，可用 `hcuExporter.hcuExporter.env.metricsLevel` 改为 Release YAML 中的 `low`。

## 产物与来源

Chart 包保留上游许可证。打包时将 Chart API 改为 `v2`，从 DaemonSet 和 Service 选择器中移除镜像版本，并为当前镜像增加 amd64 节点筛选。Chart 发布后可通过 `oci://ghcr.io/dynamia-ai/hygon/charts/hcu-exporter-charts` 和 `--version 3.0.2` 安装。 `make app` 导入同一 Release 的官方 Docker 镜像包，生成 `linux/amd64` 镜像布局。 [上游许可证](LICENSE)
