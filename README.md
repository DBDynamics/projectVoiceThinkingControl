# projectVoiceThinkingControl

- 使用 Python 编写
- 可选接入方舟大模型进行解析与“思考”（默认用规则解析；设置 `ARK_API_KEY` 后启用）
<!-- 注意：不要在README或仓库中暴露真实密钥。请通过环境变量在本地设置。 -->

import os
from volcenginesdkarkruntime import Ark

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
# 初始化Ark客户端，从环境变量中读取您的API Key
client = Ark(
    # 此为默认路径，您可根据业务所在地域进行配置
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
    api_key=os.environ.get("ARK_API_KEY"),
)

# Non-streaming:
print("----- image input request -----")
completion = client.chat.completions.create(
   # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
    model="doubao-seed-1-6-251015",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                    },
                },
                {"type": "text", "text": "这是哪里？"},
            ],
        }
    ],
    
)
print(completion.choices[0].message.content)

# Streaming:
print("----- streaming request -----")
stream = client.chat.completions.create(
    model="doubao-seed-1-6-251015",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                    },
                },
                {"type": "text", "text": "这是哪里？"},
            ],
        }
    ],
    
    # 响应内容是否流式返回
    stream=True,
)
for chunk in stream:
    if not chunk.choices:
        continue
    print(chunk.choices[0].delta.content, end="")
print()

- 示例：我告诉它“苹果在120度 鸭梨在240度 西瓜在360度(0度)”，然后我说“西瓜”，程序打印 `0度` 并语音回复“找到了”；我说“葡萄”则语音回复“没有找到”。
- 运行环境：Windows
- 语音要求：中文语音逼真流畅、尽量减少机械感（使用 Microsoft Neural TTS 语音）

## 快速开始（Windows）

1. 安装 Python 3.9+（推荐 3.10/3.11）
2. 在项目根目录创建虚拟环境并安装依赖：
   - `python -m venv .venv`
   - `.venv\Scripts\Activate.ps1`（PowerShell）或 `.venv\Scripts\activate.bat`（cmd）
   - `pip install -r requirements.txt`
3. 运行程序：
   - `python main.py`

## 使用方法

- 教知识：直接输入“水果在X度”的语句（可一次输入多条）。例如：
  - `苹果在120度 鸭梨在240度 西瓜在360度`
  - 记录后将语音回复“已记录”。其中 `360度` 会被规范化为 `0度`。
- 查询：
  - 说法一：`我说 西瓜`
  - 说法二：直接输入水果名，如：`西瓜`
  - 找到会打印角度并语音回复“找到了”；未找到则语音回复“没有找到”。
- 退出：输入 `退出` 或 `exit` / `quit`

## 语音说明

- 合成：默认使用 `edge-tts` 调用微软中文神经语音（如 `zh-CN-XiaoxiaoNeural`），音色自然。
- 播放：将合成音频保存为临时 MP3 文件并自动播放，再删除临时文件。
- 识别（新增）：使用 `Vosk` 的中文模型进行离线识别。进入语音模式后，你可以直接说：
  - “西瓜在120度” → 程序记录并语音回复“已记录”。
  - “我说西瓜” 或 “我说西瓜是” → 程序查询并打印角度，同时语音回复“找到了”。
  - 支持中文数字：如“一百二十度”“一百度”“一二零度”等都会被正确解析为 120。

### 下载中文模型

- 下载 Vosk 中文小模型（约 50MB）：`vosk-model-small-cn-0.22`
- 解压到 `models/vosk-model-small-cn-0.22`
- 若你将模型放到其它路径，可通过环境变量 `VOSK_MODEL_DIR` 指定目录。

### 进入语音模式

- 在程序交互界面输入：`语音模式` 或 `voice`
- 说“退出/结束/停止”会退出语音模式。

## 可选：接入大模型“思考”

- 安装依赖：`pip install volcengine-python-sdk`
- 设置环境变量以启用方舟解析：
  - 必需 `ARK_API_KEY`
  - 可选 `ARK_BASE_URL`（默认 `https://ark.cn-beijing.volces.com/api/v3`）
  - 可选 `ARK_MODEL_ID`（默认 `doubao-seed-1-6-251015`）
- 启用后，程序在规则解析不匹配时会调用方舟大模型来：
  - 提取“X在Y度”并返回整数角度（支持中文数字与口语噪声）
  - 解析查询短语（如“我说西瓜是”）以获得查询对象
- 未设置上述环境变量时，程序继续使用内置规则与语音识别纠正规则。

### 在 Windows PowerShell 设置环境变量示例

- 当前会话生效（关闭终端后失效）：
  - `$env:ARK_API_KEY = '你的密钥'`
  - 验证：`echo $env:ARK_API_KEY`
- 永久写入用户环境（新开终端生效）：
  - `setx ARK_API_KEY "你的密钥"`
  - 重新打开终端后运行：`python main.py`
- 使用虚拟环境时，先激活：`.venv\Scripts\Activate.ps1`，再设置环境变量并运行程序。

## 目录结构

```
projectVoiceThinkingControl/
├── main.py          # 交互式主程序（录入、查询、语音回复）
├── brain.py         # 记忆与知识解析（规则 + 可选LLM）
├── tts.py           # 语音合成与播放（edge-tts + playsound）
└── requirements.txt # 依赖清单
```

## 小提示

- Windows 上若 PowerShell 执行策略受限，可先运行：`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- 首次安装依赖后，若播放卡顿，请检查网络状况或关闭占用音频设备的程序。