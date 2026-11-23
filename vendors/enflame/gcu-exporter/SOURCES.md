# GCU Exporter v3.6.5 对应源码

从本版本的 GitHub Release 下载 `gcu-exporter-v3.6.5-sources.tar`。源码包包含 Exporter 的固定上游归档（含 vendor 依赖）、镜像构建配方，以及从 Debian 归档获取的、与固定基础镜像软件包版本对应的 Debian 源码。解包后可用 `sha256sum -c DEBIAN-SHA256SUMS` 核对 Debian 文件。 [源码下载](https://github.com/dynamia-ai/accelerator-artifacts/releases/tag/release%2Fenflame%2Fgcu-exporter%2Fv3.6.5)

| 输入 | 固定版本 |
| --- | --- |
| Exporter 源码 | `a83264c908916e94480a42cddcd0615c56def9e6` |
| Debian 基础镜像 | `sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc` |
| Debian 软件包快照 | `20261104T212339Z` |

发布时先把对应源码包上传至相同版本 tag 的 GitHub Release，再批准镜像的 GHCR 发布任务。Debian 基础镜像的构建脚本和软件包元数据由 Debian 官方镜像项目维护。 [Debian 基础镜像构建说明](https://github.com/debuerreotype/docker-debian-artifacts)
