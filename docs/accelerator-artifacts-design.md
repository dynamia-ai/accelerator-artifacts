# 加速卡组件构建与分发设计

`dynamia-ai/accelerator-artifacts` 集中维护 Kubernetes Device Plugin 和硬件指标 Exporter 的构建配方、上游版本和分发记录。正式构建从指向 `main` 已审阅提交的项目发布 tag 读取配方，再按固定 SHA 获取上游源码。少量构建适配留在组件目录中，组件接入采用普通 Git 文件和明确声明的依赖，无需配置 Git submodule 或逐个维护厂商 fork。

首个试点是寒武纪 Cambricon Kubernetes Device Plugin `v2.5.0`，目标平台为 `linux/amd64`。海光 HCU Device Plugin 和 HCU Exporter 用于验证目录设计能覆盖同一厂商下独立发版的多个组件。Intel GPU Device Plugin 后续再接入。首版发布容器镜像到 GitHub Container Registry（GHCR）。Helm Chart、离线包和 docs-site 集成按后续需求设计。

## 设计状态

本文记录首版设计和后续接入条件。已确定的范围包括集中构建、按组件固定上游源码、发现正式 Release 后直接提更新 PR，以及由人工或 Agent 复核。寒武纪作为首个试点，海光作为扩展验证样本。仓库通过 Renovate 配置跟踪组件的正式 Release，托管 App 接入待验证。

上线前需要分别确认三件事。仓库管理员验证 Renovate PR 的签名、DCO 和公开 CI。组件维护者核对寒武纪 SDK 的构建使用许可，以及两份运行库的公开分发许可。发布维护者验证私有暂存、GHCR 包权限和产物流转。寒武纪的本地构建验证可以先于公开发布进行。

## 目录与上游元数据

`<vendor>/<component>` 是组件标识，例如 `cambricon/device-plugin`。版本检查遍历 `vendors/<vendor>/<component>/`，逐个读取 `upstream.yaml`，无需维护中央组件清单。厂商根目录可以用 `vendor.yaml` 记录名称和官网，构建和版本检查无需读取它。CI 检查组件路径与三个必填字段，报告缺失或无效的 `upstream.yaml`。

```text
vendors/
├── cambricon/
│   ├── vendor.yaml
│   └── device-plugin/
│       ├── upstream.yaml
│       ├── Dockerfile
│       ├── build.sh
│       ├── platform
│       ├── LICENSING.md
│       └── README.md
└── hygon/
    ├── vendor.yaml
    ├── hcu-device-plugin/
    │   └── upstream.yaml
    └── hcu-exporter/
        └── upstream.yaml
```

寒武纪试点的 `vendors/cambricon/device-plugin/upstream.yaml` 如下。三个字段均为必填字符串，按示例顺序连续书写。

```yaml
repository: "https://github.com/Cambricon/cambricon-k8s-device-plugin"
tag: "v2.5.0"
commit: "02de42d84c4043432f126a265dbb3b37d1c13792"
```

- `repository` 是上游公开源码仓库的 HTTPS URL。首版只接受 `https://github.com/<owner>/<repo>` 形式。
- `tag` 是选择的上游版本。首版识别 `vX.Y.Z` 形式的正式 Release，按三个数字比较版本。
- `commit` 是 tag 最终指向的完整 Git commit SHA。带注释的 tag 也解析到 commit。检出和构建以该 SHA 为准。更新已有版本锁时，公开 CI 会核对 base 的 tag。已锁定的 tag 被删除或移动时，检查失败并报告原 SHA 和上游现状，由维护者复核。

`upstream.yaml` 锁定上游源码。组件维护者在 `README.md` 记录安装入口和支持平台，在构建配方中记录实际使用的工具链、基础镜像、SDK 和补丁。计划公开分发产物的组件使用独立的 `LICENSING.md` 记录许可。依赖优先使用组件自身的锁定文件和校验值。接入只打 tag 或使用其他发布渠道的组件时，再扩展版本发现方式。

## 新版本直接进入更新 PR

`.github/renovate.json` 用 `custom.regex` 读取组件的 `upstream.yaml`，以 `github-releases` 为数据源。只跟踪正式发布的 `vX.Y.Z`，在同一条 PR 中更新 `tag` 和完整 commit SHA。寒武纪和两个海光组件的样本均通过本地试验。新 Release 的 tag 暂时无法解析为 commit 时，Renovate 跳过该更新。 [Renovate 自定义规则](https://docs.renovatebot.com/modules/manager/regex/) · [GitHub Releases 数据源](https://docs.renovatebot.com/modules/datasource/github-releases/)

Renovate 发现新版后直接提 PR，由人工或 Agent 复核。PR 描述提供版本对比信息和复核事项。公开 CI 校验候选的正式 Release、tag 和 SHA，并检查升级方向；更新已有版本锁时，同时校验 PR base 的 tag 与 SHA。即使 Renovate 在旧 tag 移动后仍提出更高版本，该 PR 的检查也会失败。组件维护者在合入前复核配方、构建输入和版本适用的许可声明。

Dependabot 每周更新本仓库的 uv 依赖和 GitHub Actions。厂商的工具链、SDK 和基础镜像跟随组件配方，由组件维护者单独审阅。首次 Renovate PR 验证提交签名、DCO 和公开 CI。 [接入与验证步骤](operations.md#renovate-接入) · [Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/)

## 组件检查与发布路由

公开 CI 从目录生成组件矩阵，仓库级 Python 检查单独运行。每个组件检查自己的锁。包含镜像配方的目录同时提供 `Dockerfile`、`build.sh` 和一行 `platform`，例如 `linux/amd64`。`build.sh --check-public` 使用组件自己的公开上下文检查 Dockerfile。矩阵中的组件独立执行，`Public checks passed` 汇总所有检查结果。

发布 tag 使用 `release/<vendor>/<component>/vX.Y.Z`。入口从 tag 解析组件及版本，确认配方来自已审阅的 `main` 提交，并核对适用的许可。受保护的发布 job 校验签名证据。共用发布 workflow 按组件排队，覆盖镜像推送和 Release 记录。独立组件可同时发布。 [并发配置](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)

## 构建、Fork 与发布权限

| 场景 | 允许的操作 |
| --- | --- |
| 社区 fork 提 PR | 原仓库通过 `pull_request` 在 GitHub 托管的临时 runner 执行公开检查。`GITHUB_TOKEN` 只读，工作流仅使用公开输入。按仓库配置审批外部贡献者的工作流运行。 |
| 用户在自己的 fork 运行 | 用户在 fork 的 Actions 页面启用工作流后，可以手动运行公开验证。持有合规 SDK 的用户可以在自己的机器上使用同一份构建配方。 |
| 上游更新 PR | Renovate 在原仓库创建版本更新 PR。公开 CI 使用只读权限核对版本锁。 |
| 原仓库正式构建和发布 | 维护者先推送指向 `main` 已审阅提交的项目发布 tag，例如 `release/cambricon/device-plugin/v2.5.0`。授权环境以该 tag 为正式构建入口。GHCR 工作流由 tag 推送触发，也可从 `main` 手动传入 `ref`，重试已存在的项目发布 tag。独立发布 job 使用该组件要求人工审批的 GitHub Environment，镜像推送由该 job 的 `packages: write` 授权。 |

公开的 PR 检查和上游构建使用只读 Git 权限，检出后不保留 Git 凭据。外部 PR 在 `pull_request` 上运行，无 App、暂存镜像或包写入凭据。可公开构建的组件在无发布凭据的 runner 上执行上游代码。这些检查和构建产生的 PR 产物不得进入发布流程。 [GitHub fork 工作流规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories) · [GitHub Actions 安全指南](https://docs.github.com/en/actions/reference/security/secure-use)

仓库提交、公开 PR 描述、Actions 日志、缓存和产物只使用可公开的内容。私有 SDK、私有镜像地址、客户信息、内部文档和凭据留在授权环境。发布 job 使用原仓库的 `GITHUB_TOKEN` 推送 GHCR 包。包需关联原仓库并允许其 Actions 写入。独立的记录 job 使用 `contents: write` 附加公开记录。 [GitHub Actions 发布镜像](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) · [GitHub Packages 访问控制](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)

## 成品许可与分发

仓库根目录的 `LICENSE` 适用于 Dynamia 自有脚本和文档，拟采用 Apache-2.0。组件维护者为每个计划公开分发的组件维护 `vendors/<vendor>/<component>/LICENSING.md`。仅提供官方获取和安装入口的组件在 `README.md` 中说明即可。

`LICENSING.md` 记录适用的上游版本、许可证和公开来源，区分成品内的基础镜像与依赖、仅供构建使用的依赖和宿主机提供的运行库，并列明公开分发的授权状态与交付义务。涉及非公开授权时，公开文件只记录可披露的结论，原始证据保存在内部。

发布维护者在推送前核对成品与对应版本的 `LICENSING.md`。声明缺失、覆盖范围与实际产物不符，或公开分发授权待确认时，发布流程阻止推送到 GHCR。随成品按适用条款提供 `LICENSE`、`NOTICE`、第三方声明及所需源码。修改上游文件时，按其许可证保留版权声明并标注修改。 [Apache-2.0 再分发条款](https://apache.org/licenses/LICENSE-2.0.html#redistribution)

需要私有 SDK 的组件在授权环境中按项目发布 tag 构建，再上传成品到私有暂存仓库。构建证据记录构建身份、tag 指向的配方 commit 和镜像 digest。发布 job 核对这些证据和分发授权，按 digest 向 GHCR 推送。镜像目标由组件标识推导。寒武纪镜像发布到 `ghcr.io/dynamia-ai/accelerator-artifacts/cambricon/device-plugin`。打开私有暂存通道前，发布维护者需要验证它的访问范围、产物来源和凭据隔离。

使用 `skopeo copy --all --preserve-digests` 同步私有暂存镜像或获准再分发的上游成品镜像。发布 job 只校验和转移镜像，不执行上游代码。首次推送的 GHCR 包默认是私有的。维护者确认成品许可后，可将包设为公开。核对目标 digest、镜像平台和匿名拉取后，记录 job 将版本记录附加到使用已有 Git tag 的 GitHub Release。GitHub Release 可以先保留为草稿，附加记录后再公开。下游可通过记录中的公开镜像引用和 digest 获取成品。 [GHCR 包可见性](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#pushing-container-images)

发布与记录步骤核对项目 tag、许可、配方及本次使用的发布程序是否仍符合 `main` 上的版本。发布程序发生变化时，从最新 `main` 手动传入同一个项目发布 tag。workflow 执行这次 `main` 的发布代码，证据和发布记录继续使用 tag 指向的原配方 SHA。组件配方或许可发生变化时，维护者复核后另行处理。

记录包括组件标识、上游仓库、tag、源码 SHA、`accelerator-artifacts` 构建配方 commit（成品同步时记录原镜像引用和 digest）、目标镜像引用、目标 manifest 或镜像索引 digest、各平台及其 manifest digest、验证时间、对应构建配方 commit 下的 `LICENSING.md` 链接和安装入口。

## 寒武纪试点

寒武纪 `v2.5.0` 的上游项目源码采用 Apache-2.0。其安装说明要求从驱动包取得 `cndev.h` `6.5.24`，该文件未包含在所选版本的源码树中。Dockerfile 还会将 `libcndev.so` 和 `libcntopo.so` 复制到最终镜像。寒武纪组件的 `LICENSING.md` 分别记录插件源码许可、构建时获取和使用 SDK 的许可，以及两份运行库随镜像在 GHCR 公开分发的许可。后两项需要分别核对。 [寒武纪源码许可证](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/LICENSE) · [上游构建说明](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/device-plugin/README.md) · [上游 Dockerfile](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/device-plugin/Dockerfile)

试点先验证 fork PR 能跑公开检查、源码锁定可核对，以及构建配方能分别指出缺少的头文件或运行库。持有合规 SDK 的维护者在受控环境构建镜像，验证 `linux/amd64` 平台、入口文件与两份运行库。首次 Renovate PR 核对版本差异、PR 描述、签名、DCO 和公开 CI。设备注册需要在配套 MLU 宿主机上验证。GHCR 发布安排在成品分发权限确认之后。

海光验证同一厂商下的组件独立跟踪。HCU Device Plugin 和 HCU Exporter 在 `v3.0.2` 对应不同的 Release、源码 SHA 和发布资产。两者各自通过 `go.mod` 固定 `hcu-dcgm/v3`。首版版本检查跟踪两条组件 Release，共享依赖由维护者随组件升级复核。当前两个 Dockerfile 从宿主机使用 HyHAL 运行库，组件接入时在 `README.md` 记录适用的 HyHAL 版本和挂载路径。计划公开分发时，在 `LICENSING.md` 记录上游第三方声明和宿主机提供的依赖。 [HCU Device Plugin Release](https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/tag/v3.0.2) · [HCU Exporter Release](https://github.com/HYGON-AI/hcu-exporter/releases/tag/v3.0.2) · [hcu-dcgm 第三方声明](https://github.com/HYGON-AI/hcu-dcgm/blob/v3.0.2/THIRD_PARTY_NOTICES.md)

## 仓库初始化

空远端需要一个 `main` 基线才能接收第一条 PR。拟由维护者单独批准一个签名并带 DCO 的空提交作为基线，仓库内容继续经 PR 合入。

- 初始化 PR 包含仓库说明、许可证和贡献规则。签名、DCO、独立 worktree 以及公开推送和建 PR 的授权约定纳入贡献规则。
- 寒武纪试点 PR 加入目录、上游元数据、许可声明、构建配方和公开检查。公开检查有可用结果后，再配置为合入的必需检查。
- 自动更新与正式发布分开启用。Renovate 接入需完成分支保护、App 安装、签名、DCO 和 PR CI 验证。正式发布需完成成品分发授权、私有暂存和 GHCR 权限验证。
