# 寒武纪 Device Plugin 成品许可

Upstream-Tag: v2.5.0
Public-Redistribution: pending

本声明适用于源码 commit `02de42d84c4043432f126a265dbb3b37d1c13792` 的 `linux/amd64` 镜像。公开分发授权待确认。

| 内容 | 用途和许可状态 |
| --- | --- |
| `/usr/bin/k8s-device-plugin` | 镜像内的上游插件二进制。上游源码采用 Apache-2.0。配方将上游 `LICENSE` 放入 `/usr/share/doc/cambricon-device-plugin/`。成品的 Go 依赖许可、第三方声明和源码交付义务待核对。 |
| Ubuntu 22.04 | 镜像的运行时基础。各系统包的许可与源码交付义务待按成品核对。 |
| `cndev.h` 6.5.24 | 从配套驱动包取得，仅在构建阶段使用。用于构建和由此生成二进制的授权待确认。 |
| Go 1.24、编译工具及构建阶段依赖 | 仅在构建阶段使用。实际链接进二进制的依赖须纳入成品核对。 |
| `/usr/lib/libcndev.so` 和 `/usr/lib/libcntopo.so` | 镜像内的两份运行库。库版本、兼容的驱动版本和在 GHCR 公开分发各运行库的授权均待确认。 |
| MLU 驱动和宿主机工具 | 由 MLU 宿主机按上游安装说明提供。 |

发布前按实际镜像核对 `LICENSE`、适用的 `NOTICE`、第三方声明和应提供的源码。公开文件记录可披露的复核结论，授权原始证据保存在受控环境。

[上游源码许可证](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/02de42d84c4043432f126a265dbb3b37d1c13792/LICENSE) · [上游构建及宿主机要求](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/02de42d84c4043432f126a265dbb3b37d1c13792/device-plugin/README.md)
