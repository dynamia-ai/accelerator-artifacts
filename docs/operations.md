# 检查和发布组件产物

## 检查组件

在 `vendors/<vendor>/<component>/` 添加 `component.toml`、`Makefile`、`README.md` 和 `LICENSING.md`。清单声明组件版本、产物名和各产物类型。Makefile 为 `app-image` 实现 `app`，为 `helm-chart` 实现 `chart`。同一目标准备该类型的全部产物。 [产物输出约定](accelerator-artifacts-design.md#构建约定)

使用 `uv run --locked python scripts/components.py build <vendor>/<component>` 按 CI 的方式准备并检查组件产物。公开 CI 自动发现组件，每个组件运行独立任务。将 `Public checks passed` 设为合入所需的检查。

## 更新上游版本

海光组件由 Renovate 跟踪 GitHub 正式 Release。合入更新 PR 前，更新 Makefile 里的归档 SHA-256 和 `LICENSING.md`，并确认产物的实际内容与许可证。每个产物的 `approved_version` 只适用于填写的版本。昇腾组件按 GitCode 的正式版本手动更新清单、源码 commit 和打包补丁。Dependabot 管理本仓库的 uv 依赖与 GitHub Actions。 [Renovate GitHub Releases 数据源](https://docs.renovatebot.com/modules/datasource/github-releases/)

## 发布到 GHCR

1. 在原仓库预先配置 `public-ghcr` Environment 和维护者审批。允许从 `main` 与 `release/*/*/v*` 运行，并将 Environment 变量 `GHCR_PUBLISH_ENABLED` 设为 `true`。通过仓库规则限制发布 tag 的创建权限，禁止移动或删除已发布 tag。已有 GHCR 包需给本仓库的 Actions 授予写权限。 [GHCR 权限配置](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
2. 确认组件每个产物的 `approved_version` 都与清单版本一致。从已合入 `main` 的提交创建并推送发布 tag，例如 `release/ascend/npu-exporter/v26.2.0`。
3. 批准 `Publish accelerator artifacts` 的发布 job。打开运行摘要，核对每个产物的引用和 OCI digest。
4. 首次创建 GHCR 包时，在包设置中将可见性设为公开。用未登录 GHCR 的客户端拉取并核对 digest，再将引用交给文档或下游同步流程。 [包可见性设置](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)

## 重试发布

从 `main` 手动运行同一工作流，在 `ref` 填原发布 tag。任务使用该 tag 的配方，已存在且内容一致的产物会直接复用。目标 tag 内容冲突时，核对仓库与配方后用新的组件版本发布。 [发布约定](accelerator-artifacts-design.md#发布约定)
