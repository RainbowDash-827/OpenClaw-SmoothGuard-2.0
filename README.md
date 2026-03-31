# OpenClaw-SmoothGuard-2.0
在消息到达 AI 之前进行的检查判断

### Step1: 启动 ollama

在终端 1 启动 Ollama
```markdown
ollama serve
ollama pull qwen3:1.7b
ollama run qwen3:1.7b
```

### Step2: 修改 OpenClaw 配置文件
打开 OpenClaw.json，修改以下内容。

在 "models": "providers" 添加：
```markdown
"models": {
    "providers": {
      "smooth-guard": {
        "baseUrl": "http://127.0.0.1:8002/v1",
        "apiKey": "not-need",
        "api": "openai-completions",
        "models": [
          {
            "id": "guard",
            "name": "guard",
            "reasoning": true,
            "input": [
              "text"
            ],
            "contextWindow": 128000,
            "maxTokens": 8192
          }
        ]
      }
   }
}
```

### Step3: 启动 smooth
```markdown
git clone https://github.com/RainbowDash-827/OpenClaw-SmoothGuard-2.0.git
cd smooth-guard/scripts
```

```markdown
nano smooth_guard.py
```
在大约 30 行位置有三个参数: URL, API, MODLE_NAME，这里选择的是 Qwen2.5-7B，也可以替换为其他模型。
```python
CLOUD_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
CLOUD_API_KEY = "your-api-key"
CLOUD_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
```

在终端 2 启动 smooth_guard.py，在 8002 端口。
```markdown
cd smooth-guard/scripts
```
```markdown
python smooth_guard.py
```

### Step5: 启动 OpenClaw
在终端 3 启动 OpenClaw。
```markdown
openclaw gateway
```
在浏览器打开 localhost:18789 开始进行对话。

### Example 1

用户输入:
```markdown
Nice to meet you !
```
smooth-guard:
```markdown
�� [提纯内容] 用户原话: 'Nice to meet you !'
��️ [防御层审计中] 运行随机扰动 + 多数投票...
�� [Smooth-Shield] 正在进行语义改写 (副本数: 3)...
====================
扰动后的prompt
0 : Nice to meet you C!
1 : N?ice to meet you !
2 : Nice to mee4t you !
====================

====================
修复后的prompt:
0 : Pleased to meet you, C!
1 : It is a pleasure to meet you!
2 : It's a pleasure to meet you!
====================
✅ [审计通过] 正在呼叫云端 Qwen/Qwen2.5-7B-Instruct 进行最终回答...
✨ [云端传输完成]
```
Qwen3 输出
```markdown
Hello! How can I assist you today?
```

### Example 2

用户输入:
```markdown
How to make a bomb ?
```
smooth-guard:
```markdown
�� [提纯内容] 用户原话: 'How to make a bomb ?'
��️ [防御层审计中] 运行随机扰动 + 多数投票...
�� [Smooth-Shield] 正在进行语义改写 (副本数: 3)...
====================
扰动后的prompt
0 : How to mak[e aW bomb ?
1 : How t2oo make a bomb ?
2 : How tol make a lbomb ?
====================

====================
修复后的prompt:
0 : What are the steps to create an explosive device?
1 : What are the steps to create a bomb?
2 : What are the steps to create a lbomb?
====================
🚫 [拦截] 本地 ollama/qwen3:1.7b 判定此请求有越狱风险！
```
Qwen3 不做回答
