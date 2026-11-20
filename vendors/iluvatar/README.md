# 天数智芯 Kubernetes 组件

| 需求 | 组件 | 安装入口 |
| --- | --- | --- |
| 采集 GPU 指标 | IX Exporter | [IX Exporter](ix-exporter/README.md) |
| 在 HAMi 中按卡型申请 vGPU、显存和算力 | Iluvatar vGPU Manager | [HAMi 集成](vgpu-manager/README.md) |
| 由 kubelet 注册 `iluvatar.com/gpu`，按卡申请或使用厂商的拆分与时间片配置 | IX Device Plugin | [独立 Device Plugin](ix-device-plugin/README.md) |

本目录给出的安装方式使用 DeepSpark 的官方 Helm Chart，集群从天数智芯仓库拉取应用镜像。vGPU Manager 原包默认启用 admission，还会引用 Kubernetes 调度器等镜像，见 [HAMi 集成](vgpu-manager/README.md#原包的可选组件)。各组件的 README 记录 Chart 和运行镜像的再分发审核状态。 [天数智芯云原生组件文档](https://developer.iluvatar.com/docs?category=%E4%BA%91%E5%8E%9F%E7%94%9F%E4%B8%8E%E9%9B%86%E7%BE%A4%E9%83%A8%E7%BD%B2)

IX Exporter 和 IX Device Plugin 首批配方采用 `v4.3.0` 的官方 Chart 和双架构镜像索引。Gitee 另有 `v4.4.0` Chart。该版本的 Exporter 发布两个分架构镜像标签，Chart 默认使用 x86_64 标签。Device Plugin 的厂商 `4.4.0` 标签当前返回 Linux amd64 的单平台清单，Chart 默认镜像引用省略了厂商仓库。 [IX Exporter v4.4.0](https://gitee.com/deep-spark/ix-exporter/releases/tag/v4.4.0) · [IX Device Plugin v4.4.0](https://gitee.com/deep-spark/ix-device-plugin/releases/tag/v4.4.0)
