# 加速卡组件产物分发设计

本仓库按厂商和组件管理 Kubernetes Device Plugin、硬件指标 Exporter 及其部署产物。优先搬运厂商成品，必要时复用上游打包配方。公开发布目标为 GitHub Container Registry（GHCR），公司内部的 ACR 同步由独立流程负责。

## 厂商与组件目录

`vendors/<vendor>/<component>/` 对应一个可独立更新和发布的上游组件。厂商与组件目录均使用小写短横线命名。厂商暂时只提供官方入口时，在厂商目录维护 `README.md`。接入分发时，组件目录只需增加自己的清单、构建入口和说明。

```text
vendors/
  ascend/
    npu-exporter/
      README.md
      LICENSING.md
      component.toml
      Makefile
      standalone.patch
  cambricon/
    README.md
  hygon/
    hcu-device-plugin/
      README.md
      LICENSING.md
      component.toml
      Makefile
    hcu-exporter/
      README.md
      LICENSING.md
      component.toml
      Makefile
```

`component.toml` 声明组件版本和任意数量的命名产物。组件版本使用 `vX.Y.Z`，仅含运行镜像的组件也可使用四段版本号。每个产物指定 `kind`，可填写已确认允许再分发的 `approved_version`。`helm-chart` 对应 Helm OCI Chart，`app-image` 对应运行镜像，两种类型可以出现在同一个清单中。Chart 仅引用的外部镜像由集群直接拉取，从组件 README 查找其来源和安装条件。

```toml
version = "v1.2.3"

[artifacts.device-plugin]
kind = "helm-chart"
approved_version = "v1.2.3"

[artifacts.plugin]
kind = "app-image"
approved_version = "v1.2.3"

[artifacts.init]
kind = "app-image"
approved_version = "v1.2.3"
```

组件 README 记录官方获取和安装方式。`LICENSING.md` 按版本列出每个产物的再分发依据和交付义务。许可待确认时仍可本地和 CI 打包。正式发布要求清单内每个产物的 `approved_version` 都等于本次发布版本。

## 构建约定

从组件目录运行 `make app` 准备清单中的全部运行镜像，运行 `make chart` 打包全部 Chart。组件只实现已声明类型的目标。工作流调用同一组目标。Makefile 从清单读取版本，固定上游输入并核对版本或校验和。默认输出到组件的 `dist/`，也可通过 `OUTPUT_DIR` 指定其他位置。每个产物写入以产物名命名的子目录。

| 产物类型 | 输出 |
| --- | --- |
| `helm-chart` | `<artifact>-<chart-version>.tgz`。Chart 名称等于产物名，Chart 版本是组件版本去掉前导 `v` 后的三段版本号。 |
| `app-image` | `image-source`。文件包含一行 Skopeo 源引用，例如构建目录中的 `oci:/…/image:artifact`，或者使用 digest 固定的厂商 `docker://…@sha256:…`。 |

厂商提供 Docker 镜像包时，先校验归档 SHA-256，再用 Skopeo 导入本地 OCI 布局。厂商提供镜像仓库时，按 digest 复制，保留多架构索引及所有平台。只有确需从源码构建时才复用上游配方，逐平台使用原生 runner，禁止使用 QEMU。Chart 脚本复用上游文件和工具，组件目录保留必要的打包补丁。

## 发布约定

从已合入 `main` 的提交创建 `release/<vendor>/<component>/<version>` tag。一次发布覆盖该组件版本的全部产物。同一组件的发布串行，不同组件可并行。在 `main` 手动重试时输入原发布 tag，仍使用该 tag 的配方。

设 `BASE` 为 `ghcr.io/dynamia-ai/accelerator-artifacts/<vendor>/<component>`。

| 产物 | GHCR 引用 |
| --- | --- |
| 运行镜像 | `${BASE}/images/<artifact>:<version>` |
| OCI Helm Chart | `oci://${BASE}/charts/<artifact>`，以 Helm 的 `--version` 选择版本 |

发布前准备全部产物，将 Chart 归档的成员顺序和时间戳规范化，再检查目标版本。已经存在且内容一致的产物可复用。内容不同或查询出错时中止。Skopeo 按 digest 保真复制镜像，Helm 推送 Chart，Actions 摘要记录各产物的引用与 OCI digest。已发布的产物在后续步骤失败时可通过同一 tag 重试。仅原仓库受保护的发布 job 有 GHCR 写权限，PR 检查只准备本地产物。 [Helm OCI 规范](https://helm.sh/docs/topics/registries/) · [Skopeo 复制选项](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md)

## 首版分发与厂商接入计划

| 厂商 | 规划组件与产物 | 接入条件 |
| --- | --- | --- |
| 海光 HCU | `hygon/hcu-device-plugin`、`hygon/hcu-exporter`，各 1 个应用镜像 | 首版配方使用各自的官方 `v3.0.2` Docker 镜像包。确认各成品及随包运行库的公开再分发条款后启用发布。 [Device Plugin Release](https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/tag/v3.0.2) · [Exporter Release](https://github.com/HYGON-AI/hcu-exporter/releases/tag/v3.0.2) |
| 华为昇腾 | `ascend/npu-exporter`，1 个 OCI Helm Chart | 首版单独打包 MindCluster `v26.2.0` 子 Chart。集群从 AscendHub 获取应用镜像。昇腾 Device Plugin 沿用现有 Dynamia 安装入口。 |
| 天数智芯 | `iluvatar/ix-exporter`、`iluvatar/vgpu-manager`、`iluvatar/ix-device-plugin` | 优先核对 `ix-exporter` 的官方 Chart 与双架构镜像，两类产物各自审核。再评估 HAMi 路径的 vGPU Manager 与独立 Device Plugin。 [IX Exporter Release](https://github.com/Deep-Spark/ix-exporter/releases/tag/v4.3.0) |
| AMD | `amd/device-metrics-exporter`，官方应用镜像和 Chart 候选 | 核对 ROCm Exporter 成品依赖与分发条款。AMD Device Plugin 沿用 HAMi 社区版本。 [ROCm Exporter Helm 安装](https://instinct.docs.amd.com/projects/device-metrics-exporter/en/latest/installation/kubernetes-helm.html) |
| 昆仑芯 | `kunlunxin/dcxm-exporter`，官方镜像包候选 | 核对 DCXM 包格式和分发条款。TKE 的插件和 Exporter 沿用云服务安装入口。 |
| 燧原、沐曦、摩尔线程 | `enflame/gcu-exporter`、`metax/mx-exporter`、`mthreads/mtgpu-exporter` | 从厂商确认固定版本、获取方式及成品分发条款。各家的 Device Plugin 先沿用厂商安装入口。 |
| 寒武纪 | Device Plugin、MLU Exporter 的官方安装入口 | 构建需要配套驱动包，厂商目录仅提供获取与安装说明。 |
| NVIDIA、AWS Neuron、平头哥 PPU、Intel | 沿用官方镜像、Chart 或云服务安装入口 | 首版通过现有渠道获取。按明确的分发需求评估具体成品。 |
| 瀚博、壁仞、太初元碁 | 沿用 HAMi 或厂商安装入口 | 接入前先确认可获取的组件、交付方式与公开分发条件。 |

计划中的厂商在确认首个产物后创建组件目录，由清单自动加入 CI。Hygon 的正式 GitHub Release 由 Renovate 提出版本更新，维护者同时更新归档校验和与许可记录。昇腾按 GitCode 正式发布手动更新源码 commit 与打包补丁。Dependabot 只管理本仓库的工具与 GitHub Actions。
