# 自动更新与镜像发布

## 组件检查

在 `vendors/<vendor>/<component>/` 添加 `upstream.yaml`，公开 CI 会自动加入该组件的检查任务。按 `repository`、`tag`、`commit` 的顺序连续书写字段。组件提供镜像配方时，同时添加 `Dockerfile`、`build.sh` 和 `platform`。`platform` 写一行支持的平台，例如 `linux/amd64`。通过 `build.sh --check-public` 检查 Dockerfile，公开检查入口只使用可公开的输入。

实际构建使用目标平台对应的原生 runner 和 Docker daemon。寒武纪 `linux/amd64` 构建会先核对 Docker daemon 的平台。平台不符时，切换到原生 amd64 构建环境后再运行。

将 `Public checks passed` 配置为合入所需检查。它汇总仓库级 Python 检查和各组件检查。组件检查失败时，其他组件继续运行。

## Renovate 接入

`.github/renovate.json` 只跟踪组件的正式 GitHub Release。配置使用托管 App 的 `renovate[bot]` 作者身份添加 `Signed-off-by`，并请求 GitHub 代签。安装 App 前，确认分支保护要求通过 PR 合入、公开检查和签名，并将 App 排除在绕过名单之外。用获准的试验 PR 核对实际提交作者、签名、DCO、版本对比信息和只读公开 CI。验证后，由人工或 Agent 复核 Renovate 直接创建的更新 PR。 [托管 App 接入](https://docs.renovatebot.com/getting-started/installing-onboarding/)

公开 CI 会检查新旧锁定值对应的 tag 与 SHA。旧 tag 被移动或删除时，由组件维护者复核后处理。Renovate App 尚未接入时，可通过普通 PR 更新 `upstream.yaml`。

## 仓库依赖更新

Dependabot 每周检查本仓库的 uv 项目依赖和 GitHub Actions 引用。依赖 PR 运行只读公开检查，由维护者审阅。厂商组件的构建依赖和基础镜像按组件配方固定，变更由组件维护者单独审阅。Python 解释器版本和 CI 使用的 uv 工具版本由维护者更新。

## 正式发布启用条件

寒武纪的[成品许可](../vendors/cambricon/device-plugin/LICENSING.md)当前为 `pending`。确认 SDK 构建使用、两份运行库各自的公开分发许可和实际第三方义务后，经 PR 更新 `LICENSING.md`。保留一行 `Upstream-Tag: <tag>` 及一行 `Public-Redistribution: approved`，正文记录适用的实际产物。

- 在受控构建环境先验证试点镜像和 MLU 设备注册。正式构建以已推送的项目发布 tag 为入口。配置私有暂存仓库和可信构建者签名，发布流程只接受按 digest 定址的暂存成品。
- 为每个组件预先创建 `public-ghcr-<vendor>--<component>` Environment 并配置人工审批。寒武纪使用 `public-ghcr-cambricon--device-plugin`，允许 `main` 和 `release/cambricon/device-plugin/v*`。限制该类 tag 的创建权限，禁止移动或删除已用于发布的 tag。发布 job 使用该次运行的 `GITHUB_TOKEN` 和 `packages: write` 推送 `ghcr.io/dynamia-ai/accelerator-artifacts/<vendor>/<component>`。如果包已存在，确认已关联本仓库，并已给本仓库的 Actions 授予写权限。将此工作流设为 GHCR 镜像版本 tag 的唯一写入方。 [GHCR 认证和推送](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- 在对应的受保护 Environment 中配置暂存变量和 secrets。确认成品具备公开分发授权后，再设置仓库变量 `PUBLIC_RELEASE_ENABLED=true`。

| 配置类型 | 名称 |
| --- | --- |
| Environment 变量 | `STAGING_BUILDER`、`STAGING_BUILDER_PUBLIC_KEY` |
| Environment secrets | `STAGING_IMAGE_REPOSITORY`、`STAGING_AUTH`、`STAGING_EVIDENCE`、`STAGING_SIGNATURE` |

`STAGING_AUTH` 是只读的容器认证 JSON。其 `auths` 的唯一键是 `STAGING_IMAGE_REPOSITORY` 的 registry 主机名，不带协议或路径。可信构建者使用受控私钥对 `STAGING_EVIDENCE` 的原始 JSON 字节执行 SHA-256 分离签名，`STAGING_SIGNATURE` 保存签名的单行 Base64。JSON 只能包含 `component`、`upstream_repository`、`upstream_tag`、`upstream_commit`、`recipe_commit`、`licensing_sha256`、`builder`、`platform`、`source_repository` 和 `digest`。其中 `licensing_sha256` 为对应配方 commit 下 `LICENSING.md` 的字节哈希。签名须在受控构建流程核验实际镜像后生成。

维护者为已合入 `main` 的配方创建并推送项目发布 tag，例如 `release/cambricon/device-plugin/v2.5.0`。tag 中的上游版本必须与该提交的 `upstream.yaml` 一致。tag 推送触发公开发布工作流，授权环境也以同一 tag 为正式构建入口。完成暂存和签发后再批准发布 job。若证据尚未就绪，等就绪后可从 `main` 手动运行 `Publish accelerator image`，在 `ref` 中填写同一个已存在的项目发布 tag。可填写 tag 名称，也可加 `refs/tags/` 前缀。发布 job 验证签名、digest 和平台后推送 GHCR。已有相同 digest 时重新核验，已有不同 digest 时中止。相同组件的发布和重试排队，其他组件可同时发布。

GHCR 新包默认是私有的。首推会保存镜像，但匿名校验会失败。具备包管理权限的维护者确认许可后，在包设置中将其设为公开，再重跑失败的发布 job。匿名拉取通过后，记录 job 为现有 tag 创建 Release 草稿或使用已有的草稿，附加公开 JSON 后发布 Release。 [设置包可见性](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#about-setting-visibility-and-access-permissions-for-packages)

重试时如果 `main` 已推进，工作流核对发布 workflow、校验代码、组件版本锁、许可和构建配方是否仍一致。发布程序更新后，用最新 `main` 手动重试同一 tag。workflow 和脚本来自本次运行的 `main`，`ref` 对应的原配方 SHA 用于验证证据。若组件配方或许可有变化，先复核成品和证据。工作流只使用已存在且通过验证的项目 tag。 [GitHub tag 触发规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push)

正式发布工作流接收已签名的暂存证据。授权构建环境还需接入私有暂存上传和证据签发。
