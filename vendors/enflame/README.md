# 燧原 GCU

- GCU Exporter 使用燧原 `v3.6.5` 的公开源码构建镜像，也可通过本仓库打包的独立 Helm Chart 部署。 [GCU Exporter 构建与部署说明](gcu-exporter/README.md)
- GCU Device Plugin 的固定源码提交提供独立 Helm Chart，默认镜像为 `artifact.enflame.cn/enflame_docker_images/enflame/k8s-device-plugin:v2.0.0`。匿名查询未能连接厂商仓库读取镜像清单。安装前向厂商确认拉取方式，或按官方说明构建镜像并覆盖 `image.repository` 和 `image.tag`。本仓库保留官方安装入口。 [固定版本 Chart 源码](https://github.com/EnflameTechnology/k8s-device-plugin/tree/e39a8a779f7072679e75efa8eb44f91271185c8b/deployments/helm/enflame-device-plugin) · [官方构建和安装说明](https://github.com/EnflameTechnology/k8s-device-plugin/blob/e39a8a779f7072679e75efa8eb44f91271185c8b/README.md)
