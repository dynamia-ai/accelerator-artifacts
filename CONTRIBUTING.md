# 贡献规则

- 从最新 `main` 创建独立 Git worktree 和新分支。初始 `main` 基线由维护者单独批准和建立。
- 使用 Conventional Commits。执行本地 `git commit -S -s` 前，检查环境变量、仓库配置和命令行覆盖的实际 author、committer 与 GPG 密钥。使用签名子密钥时检查所属主密钥。实际 committer 邮箱必须匹配主密钥的有效 UID 邮箱。配置不一致时先纠正，再提交。
- 向公开仓库推送或创建 PR 前取得明确授权。通过 `gh` 操作 GitHub 资源，创建 PR 或 Issue 时使用 `--body-file`。
- 可发布组件按 [组件目录约定](docs/accelerator-artifacts-design.md#厂商与组件目录) 提供 `component.toml`、`Makefile` 和 `README.md`。上游提供 `LICENSE` 文件时保留原文。
- 通过 uv 管理 Python 开发依赖。改动依赖时一并提交 `pyproject.toml` 和 `uv.lock`。使用 `uv run --locked ruff format scripts tests` 格式化 Python 文件。
- 提交前运行[公开检查](README.md#运行公开检查)。将私有 SDK、私有镜像地址、授权原件和凭据保留在受控环境。
- 镜像仓库之间的成品同步使用 `skopeo`。
