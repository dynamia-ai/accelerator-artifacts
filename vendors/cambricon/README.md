# 寒武纪 MLU

本仓库暂不分发寒武纪 Kubernetes Device Plugin 和 MLU Exporter 的镜像。两者的上游构建都需要配套的寒武纪驱动软件包，例如从驱动包取得的 `cndev.h` 和随镜像打包的 `libcndev.so`。Device Plugin 的镜像还会打包 `libcntopo.so`。本仓库暂无可用于构建的配套软件包，也没有已确认可公开再分发的厂商成品镜像。

- [Kubernetes Device Plugin 官方构建与安装说明](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/device-plugin/README.md)
- [MLU Exporter 官方构建与安装说明](https://github.com/Cambricon/mlu-exporter/blob/master/README.md)
