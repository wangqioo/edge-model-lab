# Orange Pi RK3588S/RK3588 16G+256G 设备报告

采集时间：2026-06-25 01:04:14 +08:00  
登录用户：`orangepi`  
主机名：`orangepi5plus`  
原始日志：`/Users/wq/edge-audit-logs/orangepi-rk3588s-16g256g.log`、`/Users/wq/edge-audit-logs/orangepi-rk3588s-16g256g-tail.log`

## 结论

这台是三台里最适合作为边缘端侧模型部署主力机的设备：RK3588/Orange Pi 5 Plus，16GB RAM，约 226GB 根分区可用，Docker/containerd 已安装，RKNN runtime 和 demo 文件存在。当前短板是 Python ML 包未安装，`smartmontools.service` failed，且 root 密码登录可用，暴露在 FRP/公网转发环境时需要优先加固。

注：截图写的是 RK3588S，但设备树显示 `RK3588 OPi 5 Plus`、compatible 为 `rockchip,rk3588-orangepi-5-plus` / `rockchip,rk3588`。报告按系统实际识别记录。

## 硬件与系统

- 板卡：`RK3588 OPi 5 Plus`
- SoC：Rockchip RK3588
- 架构：`aarch64`
- CPU：8 核，big.LITTLE
  - Cortex-A55 集群：4 核，最高 1800 MHz，最低 408 MHz
  - Cortex-A76 集群：4 核，最高 2256 MHz，最低 408 MHz
  - 当前 governor：`ondemand`
- 内存：15 GiB，总可用约 14 GiB
- Swap/ZRAM：
  - `zram0`：7.7G，[SWAP]
  - `zram1`：200M，挂载 `/var/log`
- 系统：Orange Pi 1.2.0 Bookworm / Debian 12
- Kernel：`6.1.43-rockchip-rk3588 #1.2.0 SMP Thu Nov 21 12:08:24 CST 2024`
- systemd：252
- 运行温度：
  - SoC：35.2 C
  - bigcore0：36.1 C
  - bigcore1：36.1 C
  - littlecore：36.1 C
  - center：35.2 C
  - GPU：35.2 C
  - NPU：35.2 C

## 存储

- 主存储：`mmcblk0`，233G
- 根分区：`/dev/mmcblk0p2`，ext4，226G，总使用 2.3G，可用 222G，使用率 2%
- Boot 分区：`/dev/mmcblk0p1`，vfat，1022M，可用 916M
- `/var/log` 使用 zram，另有 `/var/log.hdd` 指向根分区中的持久日志位置
- 建议：
  - 这台最适合放模型仓库、Docker 镜像、数据缓存
  - 建议创建 `/opt/edge/models`、`/opt/edge/services`、`/opt/edge/data`
  - 由于 `/var/log` 在 zram 上，长期业务日志应写到 `/var/log.hdd` 或 `/opt/edge/logs`

## 加速器与多媒体能力

- `/dev/mali0` 存在，权限 `root:video`
- `/dev/rga` 存在，权限 `root:video`
- `/dev/dma_heap/system` 存在
- sysfs 中存在 NPU、RGA、Mali 相关节点：
  - `/sys/class/devfreq/fdab0000.npu`
  - `/sys/devices/platform/fdab0000.npu`
  - `/sys/module/rknpu`
  - `/sys/module/rockchip_rga`
  - `/sys/module/mali`
- 未发现明确的 `/dev/rknpu*` 或 `/dev/rknn*` 设备节点。需要用 RKNN demo 做实测确认。
- PCIe 设备存在：
  - Rockchip RK3588 PCI bridges
  - 两个有线网口设备在 PCIe 下，当前无链路
- USB root hubs 多，适合接相机、采集卡或外设。

## 软件环境

- 包管理：Debian bookworm / arm64
- 编译工具：
  - gcc 12.2.0
  - git 2.39.5
  - curl/wget/tar 等基础工具存在
- Python：
  - Python 3.11.2
  - pip 23.0.1
  - 当前 pip 包很少，主要是系统包：`setuptools`、`wheel`、`cryptography`、`python-apt` 等
  - 未安装 `numpy`、`opencv-python/cv2`、`onnxruntime`、`torch`、`tensorflow`、`tflite_runtime`、`rknn`、`rknnlite`
- RKNN runtime/demo：
  - `/usr/bin/rknn_server`
  - `/usr/bin/rknn_demo`
  - `/usr/bin/rknn_camera`
  - `/usr/bin/start_rknn.sh`
  - `/usr/bin/restart_rknn.sh`
  - `/usr/lib/librknn_api.so`
  - `/usr/lib/librknnrt.so`
  - `/usr/share/rknn_demo/mobilenet_ssd.rknn`
  - `/usr/local/bin/test_rknn_demo.sh`
- 容器：
  - Docker 27.3.1
  - containerd 1.7.23
  - ctr 1.7.23
  - runc 1.1.14
  - Docker buildx v0.17.1
  - Docker Compose v2.29.7

## 网络与服务

- 当前接入：`wlP2p33s0`，局域网 IP `192.168.1.52`
- 有线：
  - `enP3p49s0` down
  - `enP4p65s0` down
- 运行服务：
  - `containerd.service`
  - `frpc.service`
  - `ssh.service`
  - `NetworkManager.service`
  - `dnsmasq.service`
  - `chrony.service`
  - `wpa_supplicant.service`
  - `vnstat.service`
  - `unattended-upgrades.service`
- systemd failed units：
  - `smartmontools.service`

## 风险与注意事项

- `rknn_server --version` 会挂住 SSH 命令，不适合直接作为版本查询命令。应使用 demo、启动脚本或 SDK 工具链确认运行状态。
- root 密码登录可用。若这台通过 FRP 暴露 SSH，建议优先禁用 root 密码登录、改用 SSH key，并限制来源。
- Docker 已安装，但 NPU/GPU/RGA 在容器内能否访问需要单独验证设备映射。至少需要考虑 `/dev/mali0`、`/dev/rga`、`/dev/dma_heap`、DRM/render 设备和相关库挂载。
- `/var/log` 是 zram，业务日志不要只写这里。
- `smartmontools.service` failed 可能只是设备不支持 SMART，但会影响健康检查，应确认或 disable。

## 边缘模型部署建议

优先路线：

1. 把这台作为主力部署机，先跑 RKNN 官方 demo：`/usr/local/bin/test_rknn_demo.sh` 或 `/usr/bin/rknn_demo`。
2. 建立 Python venv，安装 `numpy`、OpenCV、`rknn-toolkit-lite2` 对应 aarch64 wheel。
3. 如果使用 Docker，先做一个最小容器验证：
   - 容器内能 import RKNN Lite
   - 能访问 RGA/GPU/NPU 相关设备
   - 能跑 `mobilenet_ssd.rknn`
4. 推理服务建议使用 Docker Compose 或 systemd 二选一。考虑三台设备统一部署时，这台可以作为容器基线。
5. 模型目录建议：`/opt/edge/models`；服务目录：`/opt/edge/services`；持久日志：`/opt/edge/logs` 或 `/var/log.hdd/edge`。

适合任务：

- 主力 RKNN 推理节点
- Docker Compose 管理多个边缘服务
- 多模型/多进程实验
- 摄像头、RGA 预处理、NPU 推理的一体化 pipeline
- 作为三台机器的基准部署环境

不建议忽略：

- SSH/root 登录安全加固
- 容器设备透传验证
- 长时间 NPU/GPU 压测和温度记录
- Docker 镜像和日志空间清理策略

