# LCKFB TaishanPi 3M RK3576 4G+64G 设备报告

采集时间：2026-06-25 01:01:37 +08:00  
登录用户：`lckfb`  
主机名：`TaishanPi-3M`  
原始日志：`/Users/wq/edge-audit-logs/lckfb-rk3576-4g64g.log`、`/Users/wq/edge-audit-logs/lckfb-rk3576-4g64g-tail.log`

## 结论

这台板子是 RK3576 / Debian 12 / 4GB RAM / 64GB eMMC 级别的轻量边缘节点。系统干净，磁盘空间充足，GPU/NPU/RGA 相关内核模块和运行库痕迹存在，但 Python 侧 ML 包和容器运行时基本未准备好。适合做小模型、单路视频/图像预处理、RKNN Lite 推理验证，不适合作为多模型并发或大模型常驻的首选机。

## 硬件与系统

- 板卡：`LCKFB TaishanPi 3M RK3576 Board`
- SoC：Rockchip RK3576
- 架构：`aarch64`
- CPU：8 核，big.LITTLE
  - Cortex-A53 集群：最高 2016 MHz，最低 408 MHz
  - Cortex-A72 集群：最高 2208 MHz，最低 408 MHz
  - 当前 governor：`ondemand`
- 内存：3.8 GiB，总可用约 3.3 GiB
- Swap：无
- 系统：Debian GNU/Linux 12 bookworm
- Kernel：`6.1.99 #10 SMP Wed May 13 20:56:05 CST 2026`
- systemd：252
- 运行温度：
  - SoC：34.2 C
  - big core：35.2 C
  - little core：35.2 C
  - DDR：34.2 C
  - NPU：34.2 C
  - GPU：34.2 C

## 存储

- 主存储：`mmcblk0`，57.8G
- 根分区：`/dev/mmcblk0p8`，ext4，56G，总使用 3.7G，可用 50G，使用率 7%
- 额外分区：
  - `/oem`：104M，可用 84M
  - `/userdata`：944M，可用 886M
- 建议：
  - 模型、容器镜像、日志不要放 `/oem`
  - 主要工作目录建议放 `/opt/edge` 或 `/home/lckfb/edge`
  - `/userdata` 太小，只适合放少量配置/状态，不适合放模型仓库

## 加速器与多媒体能力

- `/dev/mali0` 存在，权限 `root:video`
- `/dev/rga` 存在，权限 `root:video`
- `/dev/dri/card0`、`card1`、`renderD128`、`renderD129` 存在
- `/dev/dma_heap/system`、`system-uncached` 存在
- sysfs 中存在 NPU、RGA、Mali 相关节点：
  - `/sys/class/devfreq/27700000.npu`
  - `/sys/devices/platform/27700000.npu`
  - `/sys/module/rknpu`
  - `/sys/module/rockchip_rga`
  - `/sys/module/mali`
- 未发现明确的 `/dev/rknpu*` 或 `/dev/rknn*` 设备节点。RKNN 运行时可能通过 misc/sysfs/驱动内部路径访问 NPU，需要用官方 RKNN demo 做实际验证。
- V4L2/Media 节点较多，适合后续接摄像头或视频管线测试。

## 软件环境

- 包管理：`apt 2.6.1`，`dpkg` 架构 `arm64`
- APT 源：Debian 官方源
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
  - `/usr/bin/rknn_common_test`
  - `/usr/bin/start_rknn.sh`
  - `/usr/bin/restart_rknn.sh`
  - `/usr/lib/librknnrt.so`
  - RGA headers/libraries present
  - Mali/OpenCL libraries present
- 容器：
  - 未发现 Docker/containerd/podman/nerdctl/runc 输出

## 网络与服务

- 当前接入：`wlan0`，局域网 IP `192.168.1.53`
- 备用无线：`wlan1` dormant
- 有线：`end0` down
- 监听端口：
  - SSH：22
  - ADB/USB 调试相关：5555
  - strongSwan/IPsec：UDP 500、4500、1701
  - 本地端口：127.0.0.1:4894
- 运行服务：
  - `frpc.service`
  - `ssh.service`
  - `NetworkManager.service`
  - `rkaiq_3A.service`
  - `strongswan-starter.service`
  - `ntpsec.service`
- systemd failed units：0

## 风险与注意事项

- 执行 `rknn_server --version` 会导致 SSH 会话被远端关闭。后续不要把 `rknn_server` 当普通 CLI 查询版本；应使用官方启动脚本、demo 或 SDK 文档确认用法。
- 没有 swap，4GB 内存环境下不适合直接编译大工程或跑大模型转换。模型转换建议在 x86 主机完成，板端只做 `.rknn` 推理。
- 没有容器环境。如果你想统一部署方式，需要先安装 Docker 或 containerd，并处理 NPU/GPU/RGA 设备透传。
- Python 运行栈很薄，需要创建 venv 并安装 `numpy`、`opencv-python-headless` 或系统 OpenCV、`rknn-toolkit-lite2` 等依赖。

## 边缘模型部署建议

优先路线：

1. 在开发机完成 ONNX 到 RKNN 转换。
2. 在板端安装轻量运行环境：`python3-venv`、`python3-pip`、`numpy`、OpenCV、`rknn-toolkit-lite2` 对应 aarch64 wheel。
3. 用 `/usr/share/model/RK3576/mobilenet_v1.rknn` 或自带 demo 先验证 NPU。
4. 建议工作目录：`/opt/edge`，模型目录：`/opt/edge/models`，日志目录：`/var/log/edge`。
5. 先做单进程推理服务，再考虑 systemd 管理。

适合任务：

- RKNN 小模型推理验证
- 单路摄像头/图片分类/检测
- RGA 图像缩放、颜色转换预处理
- 轻量 MQTT/HTTP 边缘节点

不建议优先承担：

- 多模型并发常驻
- 大语言模型本地推理
- 大规模 Docker 镜像构建
- 长时间无散热压测

