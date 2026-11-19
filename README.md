# Dynamia Accelerator Artifacts

本仓库维护 Kubernetes Device Plugin 和硬件指标 Exporter 的上游版本锁、镜像构建配方和发布记录。获准公开分发的镜像通过 GitHub Container Registry（GHCR）发布。各组件在 `vendors/<vendor>/<component>/upstream.yaml` 中固定源码仓库、版本和完整 commit SHA。

| 组件 | 范围 |
| --- | --- |
| [寒武纪 Device Plugin](vendors/cambricon/device-plugin/README.md) | `v2.5.0`、`linux/amd64` 构建试点。公开镜像分发授权待确认。 |
| [海光 HCU Device Plugin](vendors/hygon/hcu-device-plugin/upstream.yaml) | 独立跟踪 `v3.0.2` 正式 Release 和源码。 |
| [海光 HCU Exporter](vendors/hygon/hcu-exporter/upstream.yaml) | 独立跟踪 `v3.0.2` 正式 Release 和源码。 |

## 运行公开检查

使用 uv 管理 Python 环境。开发和 CI 使用 `.python-version` 固定的 Python 3.15.2。项目要求 Python 3.15 或更高版本。Shell 检查需要 Bash，在线检查另需已认证的 `gh`。 [安装 uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
uv sync --locked
uv run --locked ruff check scripts tests
uv run --locked ruff format --check scripts tests
uv run --locked python -m unittest discover -s tests -v
bash -n vendors/cambricon/device-plugin/build.sh
uv run --locked python scripts/upstream.py check --offline
uv run --locked python scripts/upstream.py check
```

运行 `uv run --locked python scripts/upstream.py poll` 可只读查看有待更新的组件版本。自动创建 PR 和正式发布需要分别启用。[启用和恢复说明](docs/operations.md) · [设计](docs/accelerator-artifacts-design.md) · [贡献规则](CONTRIBUTING.md)
