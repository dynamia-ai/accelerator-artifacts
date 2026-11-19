# 加速卡组件构建与分发设计

`dynamia-ai/accelerator-artifacts` 集中维护 Kubernetes Device Plugin 和硬件指标 Exporter 的构建配方、上游版本和分发记录。正式构建从指向 `main` 已审阅提交的项目发布 tag 读取配方，再按固定 SHA 获取上游源码。少量构建适配留在组件目录中，组件接入采用普通 Git 文件和明确声明的依赖，无需配置 Git submodule 或逐个维护厂商 fork。

首个试点是寒武纪 Cambricon Kubernetes Device Plugin `v2.5.0`，目标平台为 `linux/amd64`。海光 HCU Device Plugin 和 HCU Exporter 用于验证目录设计能覆盖同一厂商下独立发版的多个组件。Intel GPU Device Plugin 后续再接入。首版发布容器镜像到 GitHub Container Registry（GHCR）。Helm Chart、离线包和 docs-site 集成按后续需求设计。

## 设计状态

本文记录首版设计和后续接入条件。已确定的范围包括集中构建、按组件固定上游源码、发现正式 Release 后直接提更新 PR，以及由人工或 Agent 复核。寒武纪作为首个试点，海光作为扩展验证样本。首版已实现自建轮询流程，Renovate 完成了本地试验，正式接入待验证。

上线前需要分别确认三件事。仓库管理员验证 GitHub App 的签名、DCO 和 PR CI。组件维护者核对寒武纪 SDK 的构建使用许可，以及两份运行库的公开分发许可。发布维护者验证私有暂存、GHCR 包权限和产物流转。寒武纪的本地构建验证可以先于公开发布进行。

## 目录与上游元数据

`<vendor>/<component>` 是组件标识，例如 `cambricon/device-plugin`。版本检查遍历 `vendors/<vendor>/<component>/`，逐个读取 `upstream.yaml`，无需维护中央组件清单。厂商根目录可以用 `vendor.yaml` 记录名称和官网，构建和版本检查无需读取它。CI 检查组件路径与三个必填字段，报告缺失或无效的 `upstream.yaml`。

```text
vendors/
├── cambricon/
│   ├── vendor.yaml
│   └── device-plugin/
│       ├── upstream.yaml
│       ├── build.sh
│       ├── LICENSING.md
│       └── README.md
└── hygon/
    ├── vendor.yaml
    ├── hcu-device-plugin/
    │   └── upstream.yaml
    └── hcu-exporter/
        └── upstream.yaml
```

寒武纪试点的 `vendors/cambricon/device-plugin/upstream.yaml` 如下。三个字段均为必填字符串。

```yaml
repository: "https://github.com/Cambricon/cambricon-k8s-device-plugin"
tag: "v2.5.0"
commit: "02de42d84c4043432f126a265dbb3b37d1c13792"
```

- `repository` 是上游公开源码仓库的 HTTPS URL。首版只接受 `https://github.com/<owner>/<repo>` 形式。
- `tag` 是选择的上游版本。首版识别 `vX.Y.Z` 形式的正式 Release，按三个数字比较版本。
- `commit` 是 tag 最终指向的完整 Git commit SHA。带注释的 tag 也解析到 commit。检出和构建以该 SHA 为准。已锁定的 tag 被删除或移动时，停止该组件的自动更新，报告原 SHA 和上游现状。维护者复核后通过 PR 更新锁定值。

`upstream.yaml` 锁定上游源码。组件维护者在 `README.md` 记录安装入口和支持平台，在构建配方中记录实际使用的工具链、基础镜像、SDK 和补丁。计划公开分发产物的组件使用独立的 `LICENSING.md` 记录许可。依赖优先使用组件自身的锁定文件和校验值。接入只打 tag 或使用其他发布渠道的组件时，再扩展版本发现方式。

## 新版本直接进入更新 PR

轮询工作流每天运行一次，也支持手动检查。自动提 PR 仅在原仓库 `dynamia-ai/accelerator-artifacts` 的 `main` 上运行。检查流程读取公开 Release 和 Git 引用元数据。 [GitHub Actions 定时规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) · [GitHub Releases API](https://docs.github.com/en/rest/releases/releases#list-releases)

1. 分页查询上游 Releases，过滤草稿和预发布，按数字比较 `vX.Y.Z`，选择高于当前版本且未处理过的最高版本。将候选 tag 解析为完整 commit SHA。查询失败时记录受影响组件，继续检查其他组件，最后将整次运行标记为失败。
2. 每个组件同时保留一条打开的自动更新 PR。有打开的 PR 时保留其分支和审阅者的改动。已关闭且未合入的同版本 PR 默认视为已处理，维护者需要重新审阅时可手动重开。
3. 定时和手动检查共用一个并发组，运行中的写入流程继续完成。写入前重新读取 `main` 的上游锁定值，确认候选仍是升级。按 `upstream/<vendor>/<component>/<tag>` 命名分支，通过准确的 head 分支和 `main` 查找既有 PR。自动提交只改同一组件 `upstream.yaml` 的 `tag` 和 `commit`。
4. PR 创建失败时，重试先核对现有分支及其差异，再创建缺失的 PR。出现冲突时，只有查到同一 head 和 base 的 PR 才视为已完成。遇到分支内容不一致、候选已过期或上游 tag 改动，报告并保留现场，避免覆盖审阅者的改动。
5. PR 描述列出组件路径、新旧版本及 SHA、上游 Release 和版本对比链接、已运行的检查和待复核项。使用固定模板和公开链接。寒武纪的待复核项包括头文件和运行库版本、真实镜像构建结果及公开分发授权。
6. PR CI 校验元数据、tag 与 SHA、当前 base 上的升级方向和配方语法。人工或 Agent 按 PR 描述复核上游变更，包括许可条款和镜像内容。计划公开分发的组件还需确认 `LICENSING.md` 覆盖候选版本。需要调整配方、文档或许可声明时，维护者在同一条 PR 更新。必需检查通过后，由维护者决定是否合入。下一次版本检查以 `main` 的已合入版本为基准。

自动提 PR 拟使用只安装在本仓库的 GitHub App，授予 `contents: write` 和 `pull_requests: write`。GitHub 的内容写权限覆盖仓库，需用 `main` 的分支保护要求经 PR 合入、必需检查和签名，并将 App 排除在绕过名单之外。只有原仓库 `main` 的写入 job 能取得 App 凭据。使用内置 `GITHUB_TOKEN` 开 PR 时，GitHub 会让后续 PR CI 等待有写权限的用户批准。 [GitHub App 所需的权限](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app) · [GitHub 令牌触发规则](https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs)

机器人提交使用 Conventional Commits，启用前用试验 PR 核对实际机器人身份对应的签名与 `Signed-off-by`，并验证常规 PR CI 能启动。若采用 GitHub 代签，需先确认仓库接受该签名方式。维护者本地提交流程仍使用 `-S -s`。 [机器人提交签名验证](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#signature-verification-for-bots)

公开仓库连续 60 天无活动时，GitHub 会停用定时工作流。维护者可以重新启用工作流并手动补查。 [启用和停用工作流](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)

### Renovate 试点

Renovate 可接管厂商组件的正式 Release 发现和 PR 创建。试验使用 `custom.regex` 读取 `vendors/<vendor>/<component>/upstream.yaml` 中连续的 `repository`、`tag`、`commit` 三行，以 `github-releases` 为数据源。寒武纪和两个海光组件的样本均生成了同时更新版本和 commit SHA 的改动，并通过现有清单校验。草稿、预发布以及只有 Git tag 的版本会被跳过。找不到候选 tag 的 commit SHA 时，Renovate 会报告并跳过该更新。 [Renovate 自定义规则](https://docs.renovatebot.com/modules/manager/regex/) · [GitHub Releases 数据源](https://docs.renovatebot.com/modules/datasource/github-releases/)

接入时仅启用用于这些 `upstream.yaml` 的自定义规则。发现新版本后直接提 PR，由人工或 Agent 复核。可启用 Dependency Dashboard 查看更新状态，版本锁和审阅记录仍保存在清单与 PR 中。Dependabot 管理本仓库的 uv 依赖和 GitHub Actions。厂商的构建依赖、SDK 和基础镜像随组件配方固定，由组件维护者单独审阅。 [Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/)

切换前，PR CI 须核对 base 和候选清单各自的 tag 与 SHA。试验中，当前锁定 tag 被移动且同时存在更高版本时，Renovate 仍会提出升级。检查两组引用可保留现有流程的阻断条件。首次测试 PR 还须验证签名、DCO、PR 描述和公开 CI。验证通过后，再切换自动提 PR 的入口，避免两个流程同时为同一组件创建 PR。 [接入与验证步骤](operations.md#renovate-接入)

## 构建、Fork 与发布权限

| 场景 | 允许的操作 |
| --- | --- |
| 社区 fork 提 PR | 原仓库通过 `pull_request` 在 GitHub 托管的临时 runner 执行公开检查。`GITHUB_TOKEN` 只读，工作流仅使用公开输入。按仓库配置审批外部贡献者的工作流运行。 |
| 用户在自己的 fork 运行 | 用户在 fork 的 Actions 页面启用工作流后，可以手动运行公开验证。持有合规 SDK 的用户可以在自己的机器上使用同一份构建配方。 |
| 原仓库轮询 | 在 `main` 读取上游公开元数据，只在自动提 PR 的 job 使用 GitHub App 令牌。 |
| 原仓库正式构建和发布 | 维护者先推送指向 `main` 已审阅提交的项目发布 tag，例如 `cambricon-device-plugin-v2.5.0`。授权环境以该 tag 为正式构建入口。GHCR 工作流由 tag 推送触发，也可从 `main` 手动传入 `ref`，重试已存在的项目发布 tag。独立发布 job 使用要求人工审批的 GitHub Environment，镜像推送由该 job 的 `packages: write` 授权。 |

公开的 PR 检查和上游构建使用只读 Git 权限，检出后不保留 Git 凭据。外部 PR 在 `pull_request` 上运行，无 App、暂存镜像或包写入凭据。可公开构建的组件在无发布凭据的 runner 上执行上游代码。这些检查和构建产生的 PR 产物不得进入发布流程。 [GitHub fork 工作流规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories) · [GitHub Actions 安全指南](https://docs.github.com/en/actions/reference/security/secure-use)

仓库提交、公开 PR 描述、Actions 日志、缓存和产物只使用可公开的内容。私有 SDK、私有镜像地址、客户信息、内部文档和凭据留在授权环境。发布 job 使用原仓库的 `GITHUB_TOKEN` 推送 GHCR 包。包需关联原仓库并允许其 Actions 写入。独立的记录 job 使用 `contents: write` 附加公开记录。 [GitHub Actions 发布镜像](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) · [GitHub Packages 访问控制](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)

## 成品许可与分发

仓库根目录的 `LICENSE` 适用于 Dynamia 自有脚本和文档，拟采用 Apache-2.0。组件维护者为每个计划公开分发的组件维护 `vendors/<vendor>/<component>/LICENSING.md`。仅提供官方获取和安装入口的组件在 `README.md` 中说明即可。

`LICENSING.md` 记录适用的上游版本、许可证和公开来源，区分成品内的基础镜像与依赖、仅供构建使用的依赖和宿主机提供的运行库，并列明公开分发的授权状态与交付义务。涉及非公开授权时，公开文件只记录可披露的结论，原始证据保存在内部。

发布维护者在推送前核对成品与对应版本的 `LICENSING.md`。声明缺失、覆盖范围与实际产物不符，或公开分发授权待确认时，发布流程阻止推送到 GHCR。随成品按适用条款提供 `LICENSE`、`NOTICE`、第三方声明及所需源码。修改上游文件时，按其许可证保留版权声明并标注修改。 [Apache-2.0 再分发条款](https://apache.org/licenses/LICENSE-2.0.html#redistribution)

需要私有 SDK 的组件在授权环境中按项目发布 tag 构建，再上传成品到私有暂存仓库。构建证据记录构建身份、tag 指向的配方 commit 和镜像 digest。发布 job 核对这些证据和分发授权，按 digest 向 GHCR 推送。寒武纪镜像固定发布到 `ghcr.io/dynamia-ai/accelerator-artifacts/cambricon-device-plugin`。打开私有暂存通道前，发布维护者需要验证它的访问范围、产物来源和凭据隔离。

使用 `skopeo copy --all --preserve-digests` 同步私有暂存镜像或获准再分发的上游成品镜像。发布 job 只校验和转移镜像，不执行上游代码。首次推送的 GHCR 包默认是私有的。维护者确认成品许可后，可将包设为公开。核对目标 digest、镜像平台和匿名拉取后，记录 job 将版本记录附加到使用已有 Git tag 的 GitHub Release。GitHub Release 可以先保留为草稿，附加记录后再公开。下游可通过记录中的公开镜像引用和 digest 获取成品。 [GHCR 包可见性](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#pushing-container-images)

发布与记录步骤核对项目 tag、许可、配方及本次使用的发布程序是否仍符合 `main` 上的版本。发布程序发生变化时，从最新 `main` 手动传入同一个项目发布 tag。workflow 执行这次 `main` 的发布代码，证据和发布记录继续使用 tag 指向的原配方 SHA。组件配方或许可发生变化时，维护者复核后另行处理。

记录包括组件标识、上游仓库、tag、源码 SHA、`accelerator-artifacts` 构建配方 commit（成品同步时记录原镜像引用和 digest）、目标镜像引用、目标 manifest 或镜像索引 digest、各平台及其 manifest digest、验证时间、对应构建配方 commit 下的 `LICENSING.md` 链接和安装入口。

## 寒武纪试点

寒武纪 `v2.5.0` 的上游项目源码采用 Apache-2.0。其安装说明要求从驱动包取得 `cndev.h` `6.5.24`，该文件未包含在所选版本的源码树中。Dockerfile 还会将 `libcndev.so` 和 `libcntopo.so` 复制到最终镜像。寒武纪组件的 `LICENSING.md` 分别记录插件源码许可、构建时获取和使用 SDK 的许可，以及两份运行库随镜像在 GHCR 公开分发的许可。后两项需要分别核对。 [寒武纪源码许可证](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/LICENSE) · [上游构建说明](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/device-plugin/README.md) · [上游 Dockerfile](https://github.com/Cambricon/cambricon-k8s-device-plugin/blob/v2.5.0/device-plugin/Dockerfile)

试点先验证 fork PR 能跑公开检查、源码锁定可核对，以及构建配方能分别指出缺少的头文件或运行库。持有合规 SDK 的维护者在受控环境构建镜像，验证 `linux/amd64` 平台、入口文件与两份运行库。轮询验收覆盖正常开 PR、重试去重、过期候选和 PR 描述。设备注册需要在配套 MLU 宿主机上验证。GHCR 发布安排在成品分发权限确认之后。

海光验证同一厂商下的组件独立跟踪。HCU Device Plugin 和 HCU Exporter 在 `v3.0.2` 对应不同的 Release、源码 SHA 和发布资产。两者各自通过 `go.mod` 固定 `hcu-dcgm/v3`。首版版本检查跟踪两条组件 Release，共享依赖由维护者随组件升级复核。当前两个 Dockerfile 从宿主机使用 HyHAL 运行库，组件接入时在 `README.md` 记录适用的 HyHAL 版本和挂载路径。计划公开分发时，在 `LICENSING.md` 记录上游第三方声明和宿主机提供的依赖。 [HCU Device Plugin Release](https://github.com/HYGON-AI/k8s-hcu-device-plugin/releases/tag/v3.0.2) · [HCU Exporter Release](https://github.com/HYGON-AI/hcu-exporter/releases/tag/v3.0.2) · [hcu-dcgm 第三方声明](https://github.com/HYGON-AI/hcu-dcgm/blob/v3.0.2/THIRD_PARTY_NOTICES.md)

## 仓库初始化

空远端需要一个 `main` 基线才能接收第一条 PR。拟由维护者单独批准一个签名并带 DCO 的空提交作为基线，仓库内容继续经 PR 合入。

- 初始化 PR 包含仓库说明、许可证和贡献规则。签名、DCO、独立 worktree 以及公开推送和建 PR 的授权约定纳入贡献规则。
- 寒武纪试点 PR 加入目录、上游元数据、许可声明、构建配方和公开检查。公开检查有可用结果后，再配置为合入的必需检查。
- 自动更新与正式发布分开启用。自动更新需完成分支保护、App 权限、签名和 PR CI 验证。正式发布需完成成品分发授权、私有暂存和 GHCR 权限验证。
