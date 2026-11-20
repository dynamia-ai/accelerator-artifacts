# Node Feature Discovery 文件来源

对照 Kubernetes SIGs Node Feature Discovery（NFD）`v0.18.3` 的 `deployment/helm/node-feature-discovery/`，提交为 `f39ef6267b20ddeb79e717940b71bb98979c49a0`。包内附带该提交的 Apache License 2.0（`NFD-LICENSE`）。Dynamia 在下表所列含适配代码的文件开头增加来源和变更注释，保留原包的现有声明、模板行为和默认值。 [NFD v0.18.3 Chart](https://github.com/kubernetes-sigs/node-feature-discovery/tree/f39ef6267b20ddeb79e717940b71bb98979c49a0/deployment/helm/node-feature-discovery) · [NFD 许可证](https://github.com/kubernetes-sigs/node-feature-discovery/blob/f39ef6267b20ddeb79e717940b71bb98979c49a0/LICENSE)

| 包内文件 | 归属与厂商变更 |
| --- | --- |
| `crds/nfd-api-crds.yaml` | 与 NFD 同路径文件逐字节一致，保持原文件。 |
| `templates/ix-feature-discovery/_helpers.tpl` | 天数智芯适配 NFD 的 `templates/_helpers.tpl`，为名称增加 `-ixfd` 后缀，并移除 NFD worker 的帐号辅助函数。 |
| `templates/ix-feature-discovery/clusterrole.yaml` | 天数智芯适配 NFD 的同名模板，调整 master 角色的启用条件，移除 topology-updater 和 NodeResourceTopology API 相关角色规则。 |
| `templates/ix-feature-discovery/clusterrolebinding.yaml` | 天数智芯适配 NFD 的同名模板，调整 master 绑定的启用条件，移除 topology-updater 绑定。 |
| `templates/ix-feature-discovery/master.yaml` | 天数智芯适配 NFD 的同名模板，改用 `ixfd.enable`、新的配置校验和路径及厂商 NFD 镜像值。 |
| `templates/ix-feature-discovery/nfd-gc.yaml` | 天数智芯适配 NFD 的同名模板，调整启用条件和镜像值。 |
| `templates/ix-feature-discovery/nfd-master-conf.yaml` | 天数智芯适配 NFD 的同名模板，将配置生成条件改为 `ixfd.enable`。 |
| `templates/ix-feature-discovery/post-delete-job.yaml` | 天数智芯适配 NFD 的同名模板，将清理 Job 绑定到 `ixfd.enable` 并调整镜像值。 |
| `templates/ix-feature-discovery/serviceaccount.yaml` | 天数智芯适配 NFD 的同名模板，调整 master 帐号的启用条件，移除 topology-updater 和 worker 帐号区块。 |
| `templates/_helpers.tpl` | 天数智芯的 Manager、admission 辅助模板。与 NFD 的 `templates/_helpers.tpl` 对照，namespace 辅助函数逻辑一致、模板名不同，另有 Helm 通用命名和标签样板。文件标明该 namespace 片段。 |
| `values.yaml` | 天数智芯组合配置，保留了 NFD 的 `featureGates`、`postDeleteCleanup`、`master` 和 `gc` 的部分设置，加入厂商镜像、Manager、admission 和 IX Feature Discovery 配置，裁剪独立 NFD 的其他设置。 |

其余文件中，`templates/ix-feature-discovery/ix-feature-discovery.yaml` 是天数智芯的 IX Feature Discovery 工作负载及其 RBAC，调用随包的 NFD namespace helper。`templates/gpu-manager/`、`templates/gpu-admission/` 和 `Chart.yaml` 对应天数智芯组件。`.helmignore` 是 Helm 通用打包样板，与 NFD 同名文件逐字节一致并原样保留。
