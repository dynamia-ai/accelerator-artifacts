# 寒武纪 MLU

本仓库暂不分发寒武纪 Kubernetes Device Plugin 和 MLU Exporter 的镜像。两者的上游构建都需要配套的寒武纪驱动软件包，例如从驱动包取得的 `cndev.h` 和随镜像打包的 `libcndev.so`。Device Plugin 的镜像还会打包 `libcntopo.so`。本仓库暂无可用于构建的配套软件包，也没有已确认可公开再分发的厂商成品镜像。

两个组件的 `v2.5.0` 源码均含可独立渲染的 Helm Chart。默认镜像名分别为 `cambricon-device-plugin:2.5.0` 和 `cambricon-mlu-exporter:2.5.0`，未指定镜像仓库。Release 未附加镜像或打包后的 Chart。匿名查询 Docker Hub 默认路径均返回访问拒绝。取得配套驱动包后，按官方说明构建镜像，并在安装时填写 `image.repository` 和 `image.tag`。

- [Device Plugin 官方构建与安装说明](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/02de42d84c4043432f126a265dbb3b37d1c13792/device-plugin/README.md) · [Device Plugin Chart](https://github.com/Cambricon/cambricon-k8s-device-plugin/tree/02de42d84c4043432f126a265dbb3b37d1c13792/device-plugin/deploys/helm/device-plugin)
- [MLU Exporter 官方构建与安装说明](https://github.com/Cambricon/mlu-exporter/blob/d87439dc6aba9c1f4fb11d916706c6338058a714/README.md) · [MLU Exporter Chart](https://github.com/Cambricon/mlu-exporter/tree/d87439dc6aba9c1f4fb11d916706c6338058a714/depolys/helm/mlu-exporter)
