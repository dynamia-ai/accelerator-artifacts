# 寒武纪 Kubernetes Device Plugin

试点版本为 `v2.5.0`，目标平台为 `linux/amd64`。安装前按上游说明准备 MLU 驱动和宿主机工具。使用上游安装清单，通过已授权的分发渠道向 MLU 节点提供镜像，并将清单中的镜像改为该引用。[安装说明](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/02de42d84c4043432f126a265dbb3b37d1c13792/device-plugin/README.md#enabling-mlu-support-in-kubernetes)

## 在授权环境构建

使用 uv、Buildx，以及运行在原生 x86-64 主机上的隔离 Linux Docker daemon。构建脚本会核对 daemon 是否为 `linux/amd64`，平台不匹配时停止构建。uv 从仓库的 `.python-version` 读取构建脚本使用的 Python 版本。将下列输入留在工作区外，并将各环境变量设为对应文件的绝对路径。

| 环境变量 | 文件 |
| --- | --- |
| `CAMBRICON_CNDEV_HEADER` | 配套驱动包中的 `cndev.h` 6.5.24 |
| `CAMBRICON_LIBCNDEV` | 配套的 amd64 `libcndev.so` |
| `CAMBRICON_LIBCNTOPO` | 配套的 amd64 `libcntopo.so` |

从仓库根目录运行。

```bash
uv run --locked --no-dev vendors/cambricon/device-plugin/build.sh --check-inputs
CAMBRICON_AUTHORIZED_BUILD=1 uv run --locked --no-dev vendors/cambricon/device-plugin/build.sh --build
```

输入检查报告缺失文件和不匹配的 ELF 架构。维护者通过授权来源核对头文件和两份运行库的版本。构建配方使用锁定的源码 SHA、Go 1.24 和 Ubuntu 22.04，并在当前授权 daemon 中加载 `cambricon-device-plugin:v2.5.0`。脚本检查镜像平台、启动命令、插件文件和两份运行库。编译阶段从 Ubuntu 软件源安装构建依赖。维护者在授权环境记录实际使用的软件包版本和 SDK 文件摘要。设备注册需要在配套 MLU 宿主机上验证。

构建完成后脚本清理临时 BuildKit builder。按成品许可处理包含运行库的本地镜像。[成品许可](LICENSING.md)
