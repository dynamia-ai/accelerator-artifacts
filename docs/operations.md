# 自动更新与镜像发布

## 自动更新启用条件

维护者先取得公开仓库基线、推送和建 PR 的授权。建立带签名和 DCO 的 `main` 基线后，通过 PR 审阅仓库内容。公开检查首次通过后，将其配置为合入所需检查。

- 保护 `main`，要求经过 PR、必需检查及签名。GitHub App 不加入绕过名单。
- 将 App 仅安装到原仓库。授予 `contents: write` 和 `pull_requests: write`。创建限 `main` 的 `upstream-writer` Environment，在其中用 `UPSTREAM_APP_CLIENT_ID` 变量记录 App 的 Client ID，并配置 `UPSTREAM_APP_PRIVATE_KEY` secret。
- 通过另行获准的试验 PR 验证 GitHub 代签、机器人作者及邮箱、`Signed-off-by`、DCO 检查和常规 PR CI。验证后才设置仓库变量 `UPSTREAM_SIGNING_DCO_VERIFIED=true` 和 `UPSTREAM_WRITE_ENABLED=true`。

`Upstream releases` 每日检查，也可手动运行。每个组件最多保留一条打开的自动更新 PR。关闭的同版本 PR 可由维护者重开。失败后重新运行工作流。如果此前已创建匹配的签名提交，工作流继续创建缺失的 PR。分支内容与预期不同、候选过期或锁定 tag 移动时，工作流保留现场，由维护者复核。

## 仓库依赖更新

Dependabot 每周检查本仓库的 uv 项目依赖和 GitHub Actions 引用。依赖 PR 运行只读公开检查，由维护者审阅。厂商组件的构建依赖和基础镜像按组件配方固定，变更由组件维护者单独审阅。

Python 解释器版本和 CI 使用的 uv 工具版本由维护者更新。组件的上游 Release 当前由 `Upstream releases` 工作流跟踪。

## Renovate 接入

Renovate 已用寒武纪和两个海光组件完成本地试验。以下步骤用于正式接入。

1. 使用托管 GitHub App 时，在 `.github/renovate.json` 配置试验中验证过的 `custom.regex` 规则，仅匹配 `vendors/<vendor>/<component>/upstream.yaml`。保留 `repository`、`tag`、`commit` 连续三行。使用 `github-releases` 数据源并随版本更新完整源码 SHA。 [Renovate 接入文档](https://docs.renovatebot.com/getting-started/installing-onboarding/)
2. 在公开 CI 验证升级前后的 tag 和 SHA。若 base 锁定的 tag 被移走或删除，则阻止合入，由组件维护者处置。使用 Dependency Dashboard 时，配置为查看状态，更新 PR 直接进入现有审阅流程。
3. 用获准的试验 PR 核对签名和 DCO、只读公开 CI、PR 描述以及清单差异。确认更新仅修改一个组件的 `tag` 和 `commit`。寒武纪的真实构建和成品许可仍按组件要求复核。
4. 验证通过后关闭自建工作流的 `UPSTREAM_WRITE_ENABLED`，确认在途写入已结束，再启用 Renovate 常规提 PR。若需切回，先暂停 Renovate 提 PR，再恢复原工作流的写入开关。

## 正式发布启用条件

寒武纪的[成品许可](../vendors/cambricon/device-plugin/LICENSING.md)当前为 `pending`。确认 SDK 构建使用、两份运行库各自的公开分发许可和实际第三方义务后，经 PR 更新 `LICENSING.md`。保留一行 `Upstream-Tag: <tag>` 及一行 `Public-Redistribution: approved`，正文记录适用的实际产物。

- 在受控构建环境先验证试点镜像和 MLU 设备注册。正式构建以已推送的项目发布 tag 为入口。配置私有暂存仓库和可信构建者签名，发布流程只接受按 digest 定址的暂存成品。
- 为 `public-ghcr-release` Environment 配置人工审批，分别允许 `main` 分支和 `cambricon-device-plugin-v*` tag。限制该类 tag 的创建权限，禁止移动或删除已用于发布的 tag。发布 job 使用该次运行的 `GITHUB_TOKEN` 和 `packages: write` 推送 `ghcr.io/dynamia-ai/accelerator-artifacts/cambricon-device-plugin`。如果包已存在，确认已关联本仓库，并已给本仓库的 Actions 授予写权限。将此工作流设为 GHCR 镜像版本 tag 的唯一写入方。 [GHCR 认证和推送](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- 配置受保护的 Environment 变量和 secrets。确认成品具备公开分发授权后，再设置仓库变量 `PUBLIC_RELEASE_ENABLED=true`。

| 配置类型 | 名称 |
| --- | --- |
| Environment 变量 | `STAGING_BUILDER`、`STAGING_BUILDER_PUBLIC_KEY` |
| Environment secrets | `STAGING_IMAGE_REPOSITORY`、`STAGING_AUTH`、`STAGING_EVIDENCE`、`STAGING_SIGNATURE` |

`STAGING_AUTH` 是只读的容器认证 JSON。其 `auths` 的唯一键是 `STAGING_IMAGE_REPOSITORY` 的 registry 主机名，不带协议或路径。可信构建者使用受控私钥对 `STAGING_EVIDENCE` 的原始 JSON 字节执行 SHA-256 分离签名，`STAGING_SIGNATURE` 保存签名的单行 Base64。JSON 只能包含 `component`、`upstream_repository`、`upstream_tag`、`upstream_commit`、`recipe_commit`、`licensing_sha256`、`builder`、`platform`、`source_repository` 和 `digest`。其中 `licensing_sha256` 为对应配方 commit 下 `LICENSING.md` 的字节哈希。签名须在受控构建流程核验实际镜像后生成。

维护者为已合入 `main` 的配方创建并推送项目发布 tag，例如 `cambricon-device-plugin-v2.5.0`。tag 中的上游版本必须与该提交的 `upstream.yaml` 一致。tag 推送触发公开发布工作流，授权环境也以同一 tag 为正式构建入口。完成暂存和签发后再批准发布 job。若证据尚未就绪，等就绪后可从 `main` 手动运行 `Publish accelerator image`，在 `ref` 中填写同一个已存在的项目发布 tag。可填写 tag 名称，也可加 `refs/tags/` 前缀。发布 job 验证签名、digest 和平台后推送 GHCR。已有相同 digest 时重新核验，已有不同 digest 时中止。

GHCR 新包默认是私有的。首推会保存镜像，但匿名校验会失败。具备包管理权限的维护者确认许可后，在包设置中将其设为公开，再重跑失败的发布 job。匿名拉取通过后，记录 job 为现有 tag 创建 Release 草稿或使用已有的草稿，附加公开 JSON 后发布 Release。 [设置包可见性](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#about-setting-visibility-and-access-permissions-for-packages)

重试时如果 `main` 已推进，工作流核对发布 workflow、校验代码、组件版本锁、许可和构建配方是否仍一致。发布程序更新后，用最新 `main` 手动重试同一 tag。workflow 和脚本来自本次运行的 `main`，`ref` 对应的原配方 SHA 用于验证证据。若组件配方或许可有变化，先复核成品和证据。工作流只使用已存在且通过验证的项目 tag。 [GitHub tag 触发规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push)

正式发布工作流接收已签名的暂存证据。授权构建环境还需接入私有暂存上传和证据签发。
