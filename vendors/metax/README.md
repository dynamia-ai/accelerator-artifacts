# 沐曦 GPU

- **GPU 指标采集**。部署独立的 `mx-exporter` 时，可使用本仓库打包的 Helm Chart，运行镜像由沐曦提供。 [mx-exporter 获取与安装](mx-exporter/README.md)
- **Kubernetes Device Plugin**。通过沐曦 GPU Operator 部署 `gpu-device`。从厂商仓库 `oci://cr.metax-tech.com/cloud/metax-operator` 获取 Chart 需要沐曦授权，也可从软件中心获取对应版本的离线安装包。 [GPU Operator 安装手册](https://developer.metax-tech.com/api/client/document/preview/1411/k8s/02_start.html) · [沐曦软件中心](https://developer.metax-tech.com/softnova)
