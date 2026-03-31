import sys
import pathlib
import httpx
import re
import uuid
import time
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

repo_root = str(pathlib.Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from lib.defenses import smoothllm

app = FastAPI()

# ================= 配置区 =================
LOCAL_OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"

CLOUD_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
CLOUD_API_KEY = "sk-ebzdvsgnvhzgmmafruonwgdtryrvqpwvctduhpcwdhoxiliw"
CLOUD_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
# ==========================================

# 建立长连接池，调大超时以适应跨境连接
timeout_settings = httpx.Timeout(100.0, read=300.0, connect=100.0)
client_pool = httpx.AsyncClient(timeout=timeout_settings)

def get_pure_user_text(payload):
    try:
        if "messages" in payload and len(payload["messages"]) > 0:
            content = payload["messages"][-1].get("content", "")
            raw_text = next((item["text"] for item in content if item.get("type") == "text"), "") if isinstance(content, list) else content
            clean_text = re.sub(r'\[.*?GMT\+8\]', '', raw_text).strip()
            if "```json" in clean_text: clean_text = clean_text.split("```")[-1].strip()
            lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
            return lines[-1] if lines else "Hi"
    except: return "Hi"
    return "Hi"

@app.post("/v1/chat/completions")
async def smooth_proxy(request: Request):
    payload = await request.json()
    is_stream = payload.get("stream", False)

    pure_text = get_pure_user_text(payload)
    print(f"\n🔍 [提纯内容] 用户原话: '{pure_text}'")

    print(f"🛡️ [本地审计中] 正在调用 ollama/qwen3:1.7b 进行探测...")
    try:
        defense_result = await run_in_threadpool(
            smoothllm,
            prompt=pure_text,
            num_copies=10,
            timeout=100,
            OLLAMA_URL=LOCAL_OLLAMA_URL,
            API_KEY=CLOUD_API_KEY,
            API_URL=CLOUD_API_URL,
            MODEL_NAME=CLOUD_MODEL_NAME,
            max_new_tokens=500
        )
        
        if defense_result.get("verdict") != "safe":
            print(f"🚫 [拦截] 本地 ollama/qwen3:1.7b 判定此请求有越狱风险！")
            return JSONResponse(content={
                "id": f"blk-{uuid.uuid4()}",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "⚠️ **[本地防御阻断]** 您的请求未通过 ollama/qwen3:1.7b 安全审计。"}, "finish_reason": "stop"}]
            })
    except Exception as e:
        print(f"⚠️ 防御层异常: {e}, 自动放行...")

    print(f"✅ [审计通过] 正在呼叫云端 {CLOUD_MODEL_NAME} 进行最终回答...")
    
    payload["model"] = CLOUD_MODEL_NAME
    headers = {
        "Authorization": f"Bearer {CLOUD_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        req = client_pool.build_request("POST", CLOUD_API_URL, json=payload, headers=headers)
        target_resp = await client_pool.send(req, stream=is_stream)

        if is_stream:
            async def disguise_streamer():
                try:
                    async for chunk in target_resp.aiter_lines():
                        if not chunk: continue
                        if chunk.startswith("data: "):
                            if chunk == "data: [DONE]":
                                yield b"data: [DONE]\n\n"
                                break
                            yield (chunk + "\n\n").encode('utf-8')
                except Exception as e: print(f"⚠️ [流中断] {e}")
                finally:
                    await target_resp.aclose()
                    print("✨ [云端传输完成]")
            return StreamingResponse(disguise_streamer(), media_type="text/event-stream")
        else:
            rj = target_resp.json()
            return JSONResponse(content=rj)

    except Exception as e:
        print(f"❌ 云端调用失败: {e}")
        return JSONResponse(content={"error": "Cloud API Offline"}, status_code=500)

if __name__ == "__main__":
    import uvicorn

    print('\n' + '=' * 50)
    print('Smooth-Guard for OpenClaw 已启动')
    print('=' * 50 + '\n')
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error")