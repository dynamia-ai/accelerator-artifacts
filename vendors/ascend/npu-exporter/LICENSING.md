# NPU Exporter Chart 分发说明

此记录适用于 `npu-exporter` Chart `26.2.0`。打包输入为 MindCluster `v26.2.0` 的 Helm 子 Chart、NPU Exporter 部署清单及对应的父 Chart 默认值，固定源码提交 `6cb6683c8b73d1c26341bb81a2c1cefe12a855ca`。依据上游 Apache License 2.0 分发，包内附带上游 `LICENSE`，保留所打包文件的适用版权声明。 [上游许可证](https://github.com/Ascend/mind-cluster/blob/v26.2.0/LICENSE)

独立打包将父 Chart 的镜像与 310P SoC 模式默认值写入子 Chart，调用上游脚本生成 Helm 模板输入，并修正资源之间的 YAML 文档分隔符换行。

Chart 仅引用 AscendHub NPU Exporter 镜像。集群从 AscendHub 拉取镜像，并按厂商条款使用。 [AscendHub 镜像许可](https://www.hiascend.com/en-sg/legal/ascendhub-download)
