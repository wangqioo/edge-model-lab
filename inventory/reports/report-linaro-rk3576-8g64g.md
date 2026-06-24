# Linaro RK3576 8G+64G 设备报告

采集时间：2026-06-24 17:01:37 +00:00  
登录用户：`linaro`  
主机名：`linaro-alip`  
原始日志：`/Users/wq/edge-audit-logs/linaro-rk3576-8g64g.log`、`/Users/wq/edge-audit-logs/linaro-rk3576-8g64g-tail.log`

## 结论

这台板子是 RK3576 / Debian 12 / 8GB RAM / 64GB eMMC，硬件能力明显比 4GB 版本宽裕。NPU/GPU/RGA 内核与库痕迹存在，系统空间充足，适合做 RKNN 推理服务、视频预处理、轻量多进程实验。当前短板是没有容器运行时、Python ML 包未安装，且有一个 `console-setup.service` failed unit。

## 硬件与系统

- 板卡：`Rockchip RK3576 KICKPI K7 Board`
- SoC：Rockchip RK3576
- 架构：`aarch64`
- CPU：8 核，big.LITTLE
  - Cortex-A53 集群：最高 2016 MHz，最低 408 MHz
  - Cortex-A72 集群：最高 2208 MHz，最低 408 MHz
  - 当前 governor：`ondemand`
- 内存：7.7 GiB，总可用约 7.0 GiB
- Swap：无
- 系统：Debian GNU/Linux 12 bookworm
- Kernel：`6.1.75 #24 SMP Mon Nov 17 19:39:47 CST 2025`
- systemd：252
- 运行温度：
  - SoC：26.8 C
  - big core：27.8 C
  - little core：27.8 C
  - DDR：26.8 C
  - NPU：26.8 C
  - GPU：26.8 C

## 存储

- 主存储：`mmcblk2`，58.2G
- 根分区：`/dev/mmcblk2p6`，ext4，58G，总使用 3.4G，可用 52G，使用率 7%
- 分区布局比 LCKFB 板更简单，主要空间都在 `/`
- 建议：
  - 模型、日志、服务代码可统一放 `/opt/edge`
  - 如果后续装 Docker，注意 eMMC 只有 64GB，镜像缓存需要定期清理

## 加速器与多媒体能力

- `/dev/mali0` 存在，权限 `root:video`
- `/dev/rga` 存在，权限 `root:video`
- `/dev/dri/card0`、`card1`、`renderD128`、`renderD129` 存在
- `/dev/dma_heap/system` 存在
- sysfs 中存在 NPU、RGA、Mali 相关节点：
  - `/sys/class/devfreq/27700000.npu`
  - `/sys/devices/platform/27700000.npu`
  - `/sys/module/rknpu`
  - `/sys/module/rockchip_rga`
  - `/sys/module/mali`
- 未发现明确的 `/dev/rknpu*` 或 `/dev/rknn*` 设备节点。需要用 RKNN demo 做实测确认。
- V4L2/DRM/audio 节点存在，适合后续视频输入/显示/音频相关测试。

## 软件环境

- 包管理：`apt 2.6.1`，`dpkg` 架构 `arm64`
- APT 源：USTC Debian bookworm/bookworm-security/bookworm-updates/bookworm-backports
- 编译工具：
  - gcc/g++ 12.2.0
  - cmake 3.25.1
  - make 4.3
  - pkg-config 1.8.1
  - git 2.39.5
  - curl/wget/unzip/tar 已安装
- Python：
  - Python 3.11.2
  - 未发现 `pip3` 输出
  - 未安装 `numpy`、`opencv-python/cv2`、`onnxruntime`、`torch`、`tensorflow`、`tflite_runtime`、`rknn`、`rknnlite`
- 多媒体：
  - GStreamer 1.22.9
  - `glxinfo` 存在
- RKNN/RGA/GPU 库：
  - `/usr/bin/rknn_server`
  - `/usr/bin/start_rknn.sh`
  - `/usr/bin/restart_rknn.sh`
  - `/usr/lib/librknnrt.so`
  - `/usr/lib/aarch64-linux-gnu/librga.so`
  - Mali/OpenCL libraries present
  - `/usr/share/model/RK3588/mobilenet_v1.rknn`、`/usr/share/model/RK3562/mobilenet_v1.rknn` 等示例模型存在；日志片段没有完整显示 RK3576 示例路径，建议实机再列 `/usr/share/model`
- 容器：
  - 未发现 Docker/containerd/podman/nerdctl/runc 输出

## 网络与服务

- 当前接入：`wlan0`，局域网 IP `192.168.1.42`
- 有线：`end0`、`end1` down
- 监听端口：
  - SSH：22
  - ADB/USB 调试相关：5555
  - strongSwan/IPsec：UDP 500、4500、1701
- 运行服务：
  - `frpc.service`
  - `ssh.service`
  - `NetworkManager.service`
  - `strongswan-starter.service`
  - `ntpsec.service`
  - `bluetooth.service`
- systemd failed units：
  - `console-setup.service`

## 风险与注意事项

- 执行 `rknn_server --version` 会导致 SSH 会话被远端关闭。后续不要直接运行该命令查询版本。
- 没有 swap。8GB 内存足够跑较多边缘推理任务，但模型转换和大包编译仍建议在主机完成。
- 没有容器运行时。如果三台设备要统一部署，这台需要补 Docker/containerd。
- Python 运行栈很薄，需要补齐 pip、venv、RKNN Lite、NumPy/OpenCV。
- `console-setup.service` failed 多半不影响 headless 推理，但建议清理，避免后续自动化健康检查误报。

## 边缘模型部署建议

优先路线：

1. 把这台作为 RK3576 主力测试板，优先安装 RKNN Lite 运行环境。
2. 使用 systemd 管理推理服务，而不是先引入容器，减少设备透传不确定性。
3. 先用官方/示例 `.rknn` 模型确认 NPU，再接入你的业务模型。
4. 若后续要与 RK3588S 统一部署，再安装 Docker，并规划 `/opt/edge` 和 `/var/lib/docker` 的磁盘占用。

适合任务：

- RK3576 上的模型兼容性验证
- 较稳定的 Python 推理服务
- 轻量多路任务调度
- 图像/视频预处理加 RKNN 推理

不建议优先承担：

- 大模型转换
- 大量容器镜像构建
- 无监控的长时间高负载运行

