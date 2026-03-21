# 慧尖语音助手

Home Assistant 自定义集成，用于控制慧尖ESP32语音助手设备。

## 功能特性

- ✅ 支持设备自动发现（mDNS/ESPHome Discovery）
- ✅ 支持手动输入设备IP配置
- ✅ 支持密码认证连接
- ✅ 支持Noise加密通信（PSK）
- ✅ 支持明文连接模式（适用于未加密的 ESP32 固件）
- ✅ 支持多种LLM提供商（小智云、Ollama、HA Cloud、自定义API）
- ✅ 支持TTS语音合成
- ✅ 支持STT语音识别
- ✅ 支持实时日志订阅
- ✅ 支持服务调用（允许HA服务访问设备）

## 安装方法

### 方法 1：通过 HACS 安装（推荐）
1. 在 HACS 中添加自定义仓库，仓库地址：https://github.com/fangwenyi-dev/HA-YY
2. 搜索并安装 "慧尖语音助手"
3. 重启 Home Assistant

### 方法 2：手动安装
1. 下载本仓库的 ZIP 文件
2. 解压到 `custom_components/huijian_yuyin` 目录
3. 重启 Home Assistant

## 配置方法

### 添加慧尖语音助手集成

1. 在 Home Assistant 中进入 "配置" > "设备与服务" > "添加集成"
2. 搜索 "慧尖语音助手" 或 "huijian"
3. 选择配置方式：
   - **自动发现**：自动搜索局域网内的ESP32设备
   - **手动输入**：手动输入设备IP地址

### 配置参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| 主机 (Host) | ✅ | - | ESP32设备的IP地址，如 `192.168.1.100` |
| 端口 (Port) | ❌ | `6053` | ESP32设备的端口号 |
| 设备名称 | ❌ | `慧尖语音设备` | 显示名称 |
| 密码 (Password) | ✅ | - | 设备配置中设置的访问密码 |
| Noise PSK | ❌ | - | 加密通信密钥（如果设备启用了加密） |

### LLM 提供商配置

| 提供商 | 说明 |
|--------|------|
| **小智云** (默认) | 🌟 推荐，无需额外配置 |
| **Ollama** | 本地运行的LLM模型，需配置端点 |
| **HA Cloud** | Home Assistant Cloud |
| **自定义 API** | 使用自己的LLM API，需配置端点和API密钥 |

## 服务

### huijian_yuyin.tts

发送文字转语音命令到设备。

```yaml
service: huijian_yuyin.tts
data:
  entity_id: sensor.huijian_yuyin_xxx
  text: "你好，这是测试语音"
```

### huijian_yuyin.subscribe_logs

订阅设备实时日志。

```yaml
service: huijian_yuyin.subscribe_logs
data:
  entity_id: sensor.huijian_yuyin_xxx
```

## 实体

集成会自动创建以下实体：

- **传感器**：设备状态、连接信息
- **按钮**：重启设备等控制
- **二进制传感器**：在线状态

## 故障排除

### 常见错误及解决方案

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `Connection refused` | 设备未启动或IP错误 | 检查设备IP和端口，确认设备已启动 |
| `Authentication failed` | 密码错误 | 核对设备配置的访问密码 |
| `Unable to connect` | 网络不通或防火墙阻止 | 检查网络连接和防火墙设置 |
| `IndentationError` | 代码缩进错误 | 更新到最新版本 |
| `No module named 'espdiscovery'` | ESPHome Discovery未安装 | 该功能为可选，不影响核心功能 |

### 启用调试日志

在 `configuration.yaml` 中添加：

```yaml
logger:
  logs:
    custom_components.huijian_yuyin:
      level: debug
```

## 版本兼容性

- **Home Assistant版本**：2023.1 及以上
- **Python版本**：3.11 及以上
- **设备要求**：运行慧尖语音ESP32固件的ESP32设备

## 版本历史

### v0.0.3
- 优化设备连接管理，修复命令发送失败问题
- 改进 WebSocket 连接稳定性
- 支持明文连接模式（适用于未加密的 ESP32 固件）
- 修复 MCP URL 配置保存位置问题

### v0.0.2
- 更新集成配置

### v1.0.0
- 初始版本发布
- 支持设备自动发现和手动配置
- 支持多种LLM提供商
- 支持TTS和STT
