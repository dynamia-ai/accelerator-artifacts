# 检查和发布组件产物

## 检查组件

在 `vendors/<vendor>/<component>/` 添加 `component.toml`、`Makefile` 和 `README.md`。上游提供 `LICENSE` 文件时保留原文。清单声明组件版本、产物名和各产物类型。Makefile 为 `app-image` 实现 `app`，为 `helm-chart` 实现 `chart`。同一目标准备该类型的全部产物。 [产物输出约定](accelerator-artifacts-design.md#构建约定)

使用 `uv run --locked python scripts/components.py build <vendor>/<component>` 按 CI 的方式准备并检查组件产物。公开 CI 自动发现组件，每个组件运行独立任务。将 `Public checks passed` 设为合入所需的检查。

## 更新上游版本

更新组件时，设置 `component.toml` 的 `version`，更新构建输入。上游提供 `LICENSE` 文件时，同步为对应版本。发布新版时，按厂商明确列出的条件准备随包材料，并将要发布的产物的 `approved_version` 更新为 `version`。

### 准备 AMD 版本更新

在仓库根目录运行以下命令。需要可用的 `gh`、Skopeo、Helm 和 `yq`。省略 `--version` 时，脚本查询 ROCm 的最新正式 Release。

```bash
uv run --locked python -m scripts.update_amd prepare --version v1.5.4
```

脚本解析官方镜像的 `linux/amd64` digest，计算官方 Chart 归档的 SHA-256，并在临时目录运行组件构建检查。检查通过后，脚本更新工作区里的组件版本、Makefile 锁定值和 `LICENSE`，并输出制品来源。镜像或 Chart 尚未发布时，待对应制品可用后重新运行。提交前核对组件 README 中的版本引用和分发说明。

AMD PR 改动镜像仓库、组件版本或 digest 时，公开 CI 核对上游 tag 解析出的 digest。常规构建和发布直接使用已锁定的 digest。

### 更新其他组件

海光组件由 Renovate 跟踪 GitHub 正式 Release。Renovate 只更新清单的 `version`，合入更新 PR 前还需更新 Makefile 中的归档 SHA-256。昇腾组件按 GitCode 的正式版本手动更新清单、源码 commit 和打包补丁。Dependabot 管理本仓库的 uv 依赖与 GitHub Actions。 [Renovate GitHub Releases 数据源](https://docs.renovatebot.com/modules/datasource/github-releases/)

## 发布到 GHCR

1. 在原仓库预先配置 `public-ghcr` Environment 和维护者审批。允许从 `main` 与 `release/*/*/v*` 运行，并将 Environment 变量 `GHCR_PUBLISH_ENABLED` 设为 `true`。通过仓库规则限制发布 tag 的创建权限，禁止移动或删除已发布 tag。已有 GHCR 包需给本仓库的 Actions 授予写权限。 [GHCR 权限配置](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
2. 确认要发布的产物的 `approved_version` 与组件版本一致。从已合入 `main` 的提交创建并推送发布 tag。发布整个组件时使用 `release/<厂商>/<组件>/<版本>`。单独发布 Chart 等产物时使用 `release/<厂商>/<组件>/<版本>-artifact-<产物名>`，例如 `release/iluvatar/ix-exporter/v4.3.0-artifact-ix-exporter`。
3. 批准 `Publish accelerator artifacts` 的发布 job。打开运行摘要，核对每个产物的引用和 OCI digest。
4. 首次创建 GHCR 包时，在包设置中将可见性设为公开。用未登录 GHCR 的客户端拉取并核对 digest，再将引用交给文档或下游同步流程。 [包可见性设置](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)

## 重试发布

从 `main` 手动运行同一工作流，在 `ref` 填原发布 tag。任务使用该 tag 的配方，已存在且内容一致的产物会直接复用。目标 tag 内容冲突时，核对仓库与配方后用新的组件版本发布。 [发布约定](accelerator-artifacts-design.md#发布约定)
