# 华为昇腾 NPU Exporter

`make chart` 打包 MindCluster `v26.2.0` 的 NPU Exporter 子 Chart。默认镜像为 `swr.cn-south-1.myhuaweicloud.com/ascendhub/npu-exporter:v26.2.0-openeuler24.03`。310P SoC 模式使用 `--set is310P1usoc=true`。卡型、驱动及运行环境按官方安装说明准备。 [上游 Helm 安装说明](https://github.com/Ascend/mind-cluster/blob/v26.2.0/docs/zh/scheduling/03_installation_guide/02_installation/00_helm_installation.md) · [AscendHub 镜像](https://www.hiascend.com/developer/ascendhub/detail/1b1a8c3cc1ff4710bdb0222514a8a7a3) · [上游许可证](LICENSE)

Chart 发布到以下路径并公开后，使用此命令安装。

```bash
helm install npu-exporter \
  oci://ghcr.io/dynamia-ai/ascend/charts/npu-exporter \
  --version 26.2.0
```
