# 海光 HCU Device Plugin

`make chart` 打包海光 `v3.0.2` 源码中的三个独立 Device Plugin Chart。官方 Release 附件另有三份 Kubernetes YAML 和 Docker 镜像包。 `make app` 导入镜像包，生成 `linux/amd64` 镜像布局。 [官方 Release](https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/tag/v3.0.2) · [固定版本 Chart 源码](https://github.com/HYGON-AI/k8s-hcu-device-plugin/tree/9e9870a277b7038ab924ded3df7c44289c846858/deployment/helm) · [上游许可证](LICENSE)

## 选择安装模式

目标节点需要 Linux amd64、配套 HCU 驱动和 `/opt/hyhal`。Chart 使用特权 DaemonSet 并挂载 kubelet 的 `/var/lib/kubelet/device-plugins`。同一节点上只部署一种 Device Plugin 模式。安装 HAMi 或 MIG 模式前，按海光文档完成调度器部署或 MIG 切分。 [官方安装说明](https://github.com/HYGON-AI/k8s-hcu-device-plugin/blob/9e9870a277b7038ab924ded3df7c44289c846858/README.md#部署)

| 模式 | Chart | 节点条件 |
| --- | --- | --- |
| 普通或 vHCU | `k8s-hcu-plugin` | `hygon.com/hcu=true`，排除 `hcu-mode=mig` 和 `hcu=on` 节点。动态 vHCU 按厂商说明设置 `hcu-mode=share`。 |
| HAMi | `k8s-hcu-plugin-hami` | `hcu=on`。Chart 包含插件自己的 ServiceAccount 和 RBAC。 |
| MIG | `k8s-hcu-plugin-mig` | `hygon.com/hcu=true` 和 `hcu-mode=mig`，挂载 `/etc/dmi_mig_config`。 |

## 安装 Chart

从仓库根目录打包。将 `CHART` 改为所选模式的 Chart 名称。

```bash
make -C vendors/hygon/hcu-device-plugin chart
CHART=k8s-hcu-plugin
helm upgrade --install "$CHART" \
	"./vendors/hygon/hcu-device-plugin/dist/$CHART/$CHART-3.0.2.tgz" \
	--namespace kube-system
```

三个 Chart 默认使用现有的 `ghcr.io/dynamia-ai/hygon/hcu-device-plugin:v3.0.2`。普通和 HAMi 模式通过 `hcuDevicePlugin.hcuDpCntr.image.repository` 和 `hcuDevicePlugin.hcuDpCntr.image.tag` 覆盖镜像，MIG 模式使用 `hcuDevicePluginMig.hcuDpCntr.image.repository` 和 `hcuDevicePluginMig.hcuDpCntr.image.tag`。原厂镜像仓库为 `harbor.sourcefind.cn:5443/hcu/admin/base/hcu-device-plugin`。使用需要认证的仓库时，在安装命名空间准备拉取 Secret 并设置 `imagePullSecrets[0].name`。

打包时保留各模式的调度与注册策略。HAMi Chart 使用 Release YAML 中的 DaemonSet 名称 `hcu-device-plugin-hami`，可与普通模式在同一命名空间管理不同节点。HAMi 的 Pod 删除和拓扑 ConfigMap 权限也沿用 Release YAML。Chart 发布后可通过 `oci://ghcr.io/dynamia-ai/hygon/charts/<Chart>` 和 `--version 3.0.2` 安装。
