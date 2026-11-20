# 昆仑芯 XPU

## DCXM Exporter 离线安装

以下步骤使用新华三安装手册第 9.4.4 节明确引用的昆仑芯 `1.0.0.1` 版本包。 [昆仑芯 BOS 版本包](https://klx-sdk-release-public.su.bcebos.com/xre/component/dcxm-exporter/1.0.0.1/dcxm-exporter-ubuntu20.04_1.0.0.1.tar.gz) · [新华三 DCXM 容器安装说明](https://www.h3c.com/cn/d_202608/2893801_30005_0.htm#_Toc237009705)

1. 在配备昆仑芯 XPU 的宿主机上安装配套驱动和 `xpu-container-toolkit`。按新华三安装手册第 9.4.3 节，运行 `sudo xpu-ctk runtime configure --set-as-default`，将 XPU Runtime 设为 Docker 的默认运行时。运行 `sudo systemctl restart docker` 使配置生效。 [新华三安装手册](https://www.h3c.com/cn/d_202608/2893801_30005_0.htm)
2. 下载并解压版本包。在解压后的目录中运行 `docker load -i dcxm-exporter-ubuntu20.04.tar.gz` 导入内层镜像。从本次导入输出的 `Loaded image:` 行中记录 DCXM Exporter 的完整镜像引用（含 tag）。 [Docker 导入示例](https://docs.docker.com/reference/cli/docker/image/load/#load-images-from-a-file---input)
3. 将下面命令中的 `IMAGE_REF` 替换为本次导入的完整镜像引用，再启动容器。示例通过 `CXPU_VISIBLE_DEVICES=all` 让容器访问所有 XPU，并添加 `SYS_ADMIN` 能力。

   ```bash
   docker run -d --name "${USER}-dcxm-exporter" \
     -e CXPU_VISIBLE_DEVICES=all --cap-add SYS_ADMIN \
     -p 0.0.0.0::9400 IMAGE_REF
   ```

4. `-p 0.0.0.0::9400` 将容器的 `9400/tcp` 映射到宿主机所有 IPv4 地址上的随机端口。启动后运行 `docker port "${USER}-dcxm-exporter" 9400/tcp` 查看实际映射，将返回的宿主机端口用于指标采集。 [Docker 端口映射查询](https://docs.docker.com/reference/cli/docker/container/port/)

外层是 gzip 压缩的 tar 归档，BOS 标示对象大小为 916,387,816 字节。已从归档读取以下条目。

| 条目 | 内容 |
| --- | --- |
| `dcxm-exporter-ubuntu20.04.tar.gz` | gzip 压缩的 tar。已读到 Docker save 格式的 `VERSION`、`json` 和 `layer.tar` 层条目。 |
| `version.txt` | DCXM Exporter `1.0.0.1`、XRE `5.0.21.14`，以及上游构建 commit。 |
| `KUNLUN-DCXM-Exporter-Dashboard-1_0.json` | Grafana 仪表盘模板。 |
| `run_dcxm_exporter.sh` | 启动脚本，包含 Prometheus 和 Grafana 容器的启动逻辑。 |

## 分发状态

`1.0.0.1` 的镜像与离线包公开再分发均待审核。昆仑芯官网法律声明第 4 节第 3 款说明，软件许可需经另行协议取得。公开下载地址、安装说明和已读取的归档条目均未提供覆盖该镜像或整包的再分发授权。发布前需取得覆盖对应成品的授权，并核对昆仑芯运行库、基础镜像及第三方组件的许可与通知义务。若分发整包，还需确认启动脚本和 Grafana 模板的条款。 [昆仑芯法律声明](https://www.kunlunxin.com/%E9%9A%90%E7%A7%81%E6%94%BF%E7%AD%96) · [昆仑芯用户协议](https://www.kunlunxin.com/%E7%94%A8%E6%88%B7%E5%8D%8F%E8%AE%AE)

本仓库尚未完整下载该 BOS 版本包。整包 SHA-256、镜像 manifest、实际 tag 和镜像平台（操作系统及 CPU 架构）仍待验证。接入 `make app` 前需完整下载厂商版本包，固定归档 SHA-256，并用 Skopeo 核对内层镜像及导入 OCI 布局。当前仅提供安装入口，公开资料中未找到独立的 DCXM Exporter Helm Chart。

## 腾讯云 TKE 安装入口

在腾讯云容器服务 TKE 中，通过集群组件管理安装 `xpu-gpu`。该组件通过 `xpu-device-plugin-daemonset` 注册 XPU 资源，并通过 `xpu-exporter` 采集指标。TKE 集群须运行 Kubernetes 1.16 或更高版本。组件仅部署在已安装昆仑芯驱动和 XRE、带有 `kunlun-device-enable=enable` 标签的 `amd64` XPU 节点上。 [腾讯云 TKE XPU 组件说明](https://cloud.tencent.com/document/product/457/138230) · [TKE 组件管理](https://cloud.tencent.com/document/product/457/81234)
