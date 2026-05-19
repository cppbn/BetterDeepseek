---

# Gemini REST API 完整使用文档

> 基于 Google AI Gemini API 官方文档整理
> 基础 URL: `https://generativelanguage.googleapis.com/v1beta/`
> 认证方式: 通过 HTTP Header `x-goog-api-key` 传入 API Key

---

## 📋 目录

1. [基础信息](#1-基础信息)
2. [文本生成](#2-文本生成-text-generation)
3. [流式输出](#3-流式输出-streaming)
4. [多轮对话](#4-多轮对话-multi-turn-chat)
5. [图片理解](#5-图片理解-image-understanding)
6. [视频理解](#6-视频理解-video-understanding)
7. [音频理解](#7-音频理解-audio-understanding)
8. [Thinking 思考推理](#8-thinking-思考推理)
9. [GenerationConfig 参数详解](#9-generationconfig-参数详解)
10. [File API 文件上传](#10-file-api-文件上传)
11. [附录：支持格式与限制](#11-附录支持格式与限制)

---

## 1. 基础信息

### API 端点

| 功能 | 端点 |
|------|------|
| **文本生成**（非流式） | `POST /v1beta/models/{model}:generateContent` |
| **文本生成**（流式） | `POST /v1beta/models/{model}:streamGenerateContent?alt=sse` |
| **文件上传** | `POST /upload/v1beta/files` |
| **Token 计数** | `POST /v1beta/models/{model}:countTokens` |

### 常用模型

| 模型 ID | 说明 |
|---------|------|
| `gemini-3-flash-preview` | Gemini 3 Flash（预览版） |
| `gemini-2.5-flash` | Gemini 2.5 Flash |
| `gemini-2.5-pro` | Gemini 2.5 Pro |
| `gemini-2.5-flash-lite` | Gemini 2.5 Flash Lite |

### 请求头

```http
x-goog-api-key: YOUR_API_KEY
Content-Type: application/json
```

---

## 2. 文本生成 (Text Generation)

### 2.1 基本文本生成

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "How does AI work?"
          }
        ]
      }
    ]
  }'
```

**响应结构：**

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          { "text": "AI (Artificial Intelligence) works by..." }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": [...]
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 6,
    "candidatesTokenCount": 128,
    "totalTokenCount": 134
  }
}
```

### 2.2 系统指令 (System Instruction)

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "system_instruction": {
      "parts": [
        { "text": "You are a cat. Your name is Neko." }
      ]
    },
    "contents": [
      {
        "parts": [
          { "text": "Hello there" }
        ]
      }
    ]
  }'
```

### 2.3 配置参数 (GenerationConfig)

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          { "text": "Explain how AI works" }
        ]
      }
    ],
    "generationConfig": {
      "stopSequences": ["Title"],
      "temperature": 1.0,
      "topP": 0.8,
      "topK": 10,
      "maxOutputTokens": 2048
    }
  }'
```

---

## 3. 流式输出 (Streaming)

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:streamGenerateContent?alt=sse" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  --no-buffer \
  -d '{
    "contents": [
      {
        "parts": [
          { "text": "Explain how AI works" }
        ]
      }
    ]
  }'
```

---

## 4. 多轮对话 (Multi-turn Chat)

每条消息需指定 `role`（`"user"` 或 `"model"`）：

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "role": "user",
        "parts": [{ "text": "Hello" }]
      },
      {
        "role": "model",
        "parts": [{ "text": "Great to meet you. What would you like to know?" }]
      },
      {
        "role": "user",
        "parts": [{ "text": "I have two dogs in my house. How many paws are in my house?" }]
      }
    ]
  }'
```

---

## 5. 图片理解 (Image Understanding)

### 5.1 通过 Base64 内联传递图片

```bash
IMG_PATH="/path/to/your/image1.jpg"
MIME_TYPE=$(file -b --mime-type "${IMG_PATH}")

if [[ "$(uname)" == "Darwin" ]]; then
  B64FLAGS="-b 0"
elif [[ "$(base64 --version 2>&1)" = *"FreeBSD"* ]]; then
  B64FLAGS="--input"
else
  B64FLAGS="-w0"
fi
IMAGE_B64=$(base64 $B64FLAGS $IMG_PATH)

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {
          "inline_data": {
            "mime_type": "'"${MIME_TYPE}"'",
            "data": "'"${IMAGE_B64}"'"
          }
        },
        {"text": "Caption this image."}
      ]
    }]
  }'
```

### 5.2 通过 URL 获取图片后传递

```bash
IMG_URL="https://goo.gle/instrument-img"
MIME_TYPE=$(curl -sIL "$IMG_URL" | grep -i '^content-type:' | awk -F ': ' '{print $2}' | sed 's/\r$//' | head -n 1)
if [[ -z "$MIME_TYPE" || ! "$MIME_TYPE" == image/* ]]; then
  MIME_TYPE="image/jpeg"
fi

if [[ "$(uname)" == "Darwin" ]]; then
  IMAGE_B64=$(curl -sL "$IMG_URL" | base64 -b 0)
elif [[ "$(base64 --version 2>&1)" = *"FreeBSD"* ]]; then
  IMAGE_B64=$(curl -sL "$IMG_URL" | base64)
else
  IMAGE_B64=$(curl -sL "$IMG_URL" | base64 -w0)
fi

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {
          "inline_data": {
            "mime_type": "'"${MIME_TYPE}"'",
            "data": "'"${IMAGE_B64}"'"
          }
        },
        {"text": "Caption this image."}
      ]
    }]
  }'
```

### 5.3 多图输入

```json
{
  "contents": [{
    "parts":[
      {"text": "What is different between these two images?"},
      {"file_data": {"mime_type": "image/jpeg", "file_uri": "FILE_URI_1"}},
      {
        "inline_data": {
          "mime_type": "image/png",
          "data": "BASE64_ENCODED_DATA"
        }
      }
    ]
  }]
}
```

### 5.4 目标检测 (Object Detection)

```json
{
  "contents": [{
    "parts":[
      {"text": "Detect all of the prominent items in the image. The box_2d should be [ymin, xmin, ymax, xmax] normalized to 0-1000."},
      {
        "inline_data": {
          "mime_type": "image/png",
          "data": "BASE64_DATA"
        }
      }
    ]
  }],
  "generationConfig": {
    "response_mime_type": "application/json"
  }
}
```

> **反算实际坐标：** `abs_x = (coord / 1000) * image_width`，`abs_y = (coord / 1000) * image_height`

---

## 6. 视频理解 (Video Understanding)

### 6.1 通过 File API 上传视频

**Step 1: 发起可恢复上传**

```bash
VIDEO_PATH="path/to/sample.mp4"
MIME_TYPE=$(file -b --mime-type "${VIDEO_PATH}")
NUM_BYTES=$(wc -c < "${VIDEO_PATH}")
DISPLAY_NAME=VIDEO
tmp_header_file=upload-header.tmp

curl "https://generativelanguage.googleapis.com/upload/v1beta/files" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -D ${tmp_header_file} \
  -H "X-Goog-Upload-Protocol: resumable" \
  -H "X-Goog-Upload-Command: start" \
  -H "X-Goog-Upload-Header-Content-Length: ${NUM_BYTES}" \
  -H "X-Goog-Upload-Header-Content-Type: ${MIME_TYPE}" \
  -H "Content-Type: application/json" \
  -d "{'file': {'display_name': '${DISPLAY_NAME}'}}" 2> /dev/null

upload_url=$(grep -i "x-goog-upload-url: " "${tmp_header_file}" | cut -d" " -f2 | tr -d "\r")
rm "${tmp_header_file}"
```

**Step 2: 上传实际字节**

```bash
curl "${upload_url}" \
  -H "Content-Length: ${NUM_BYTES}" \
  -H "X-Goog-Upload-Offset: 0" \
  -H "X-Goog-Upload-Command: upload, finalize" \
  --data-binary "@${VIDEO_PATH}" 2> /dev/null > file_info.json

file_uri=$(jq -r ".file.uri" file_info.json)
echo "File URI: ${file_uri}"
```

**Step 3: 使用上传的视频进行分析**

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"file_data": {"mime_type": "'"${MIME_TYPE}"'", "file_uri": "'"${file_uri}"'}},
        {"text": "Summarize this video. Then create a quiz with an answer key based on the information in this video."}
      ]
    }]
  }'
```

### 6.2 内联传递视频（<20MB）

```bash
VIDEO_PATH=/path/to/your/video.mp4
if [[ "$(base64 --version 2>&1)" = *"FreeBSD"* ]]; then
  B64FLAGS="--input"
else
  B64FLAGS="-w0"
fi

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {
          "inline_data": {
            "mime_type": "video/mp4",
            "data": "'$(base64 $B64FLAGS $VIDEO_PATH)'"
          }
        },
        {"text": "Please summarize the video in 3 sentences."}
      ]
    }]
  }'
```

### 6.3 通过 YouTube URL

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"text": "Please summarize the video in 3 sentences."},
        {
          "file_data": {
            "file_uri": "https://www.youtube.com/watch?v=9hE5-98ZeCg"
          }
        }
      ]
    }]
  }'
```

### 6.4 指定时间戳

```json
{
  "contents": [{
    "parts":[
      {"text": "What are the examples given at 00:05 and 00:10 supposed to show us?"},
      {"file_data": {"mime_type": "video/mp4", "file_uri": "your_file_uri"}}
    ]
  }]
}
```

### 6.5 视频裁剪与帧率控制

**裁剪（设置起止时间）：**

```json
{
  "contents": [{
    "parts":[
      {
        "file_data": {
          "file_uri": "https://www.youtube.com/watch?v=XEzRZ35urlk"
        },
        "video_metadata": {
          "start_offset": "1250s",
          "end_offset": "1570s"
        }
      },
      {"text": "Please summarize the video in 3 sentences."}
    ]
  }]
}
```

**自定义帧率：**

```json
{
  "contents": [{
    "parts":[
      {
        "inline_data": {
          "mime_type": "video/mp4",
          "data": "BASE64_DATA"
        },
        "video_metadata": {
          "fps": 5
        }
      },
      {"text": "Please summarize the video in 3 sentences."}
    ]
  }]
}
```

> 默认 FPS = 1。静态内容（如讲座）可降低 FPS；快速动作场景可升高 FPS。

---

## 7. 音频理解 (Audio Understanding)

### 7.1 通过 File API 上传音频

与视频上传流程相同（见 6.1 节），MIME 类型改为音频格式。

```bash
AUDIO_PATH="path/to/sample.mp3"
MIME_TYPE=$(file -b --mime-type "${AUDIO_PATH}")
NUM_BYTES=$(wc -c < "${AUDIO_PATH}")
DISPLAY_NAME=AUDIO
tmp_header_file=upload-header.tmp

# 发起上传
curl "https://generativelanguage.googleapis.com/upload/v1beta/files" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -D ${tmp_header_file} \
  -H "X-Goog-Upload-Protocol: resumable" \
  -H "X-Goog-Upload-Command: start" \
  -H "X-Goog-Upload-Header-Content-Length: ${NUM_BYTES}" \
  -H "X-Goog-Upload-Header-Content-Type: ${MIME_TYPE}" \
  -H "Content-Type: application/json" \
  -d "{'file': {'display_name': '${DISPLAY_NAME}'}}" 2> /dev/null

upload_url=$(grep -i "x-goog-upload-url: " "${tmp_header_file}" | cut -d" " -f2 | tr -d "\r")
rm "${tmp_header_file}"

# 上传字节
curl "${upload_url}" \
  -H "Content-Length: ${NUM_BYTES}" \
  -H "X-Goog-Upload-Offset: 0" \
  -H "X-Goog-Upload-Command: upload, finalize" \
  --data-binary "@${AUDIO_PATH}" 2> /dev/null > file_info.json

file_uri=$(jq ".file.uri" file_info.json)
echo "File URI: $file_uri"

# 分析音频
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"text": "Describe this audio clip"},
        {"file_data": {"mime_type": "'"${MIME_TYPE}"'", "file_uri": '$file_uri'}}
      ]
    }]
  }'
```

### 7.2 内联传递音频

```bash
AUDIO_PATH="/path/to/small-sample.mp3"
if [[ "$(uname)" == "Darwin" ]]; then
  AUDIO_B64=$(base64 -b 0 "$AUDIO_PATH")
else
  AUDIO_B64=$(base64 -w0 "$AUDIO_PATH")
fi

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"text": "Describe this audio clip"},
        {
          "inline_data": {
            "mime_type": "audio/mp3",
            "data": "'"${AUDIO_B64}"'"
          }
        }
      ]
    }]
  }'
```

### 7.3 获取转录 (Speech-to-Text)

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"text": "Generate a transcript of the speech."},
        {"file_data": {"mime_type": "audio/mp3", "file_uri": "your_file_uri"}}
      ]
    }]
  }'
```

### 7.4 指定时间戳转录

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"text": "Provide a transcript of the speech from 02:30 to 03:29."},
        {"file_data": {"mime_type": "audio/mp3", "file_uri": "your_file_uri"}}
      ]
    }]
  }'
```

### 7.5 高级转录（含结构化输出、情感检测、翻译）

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "file_data": {
              "file_uri": "https://www.youtube.com/watch?v=ku-N-eS1lgM",
              "mime_type": "video/mp4"
            }
          },
          {
            "text": "Process the audio file and generate a detailed transcription.\n\nRequirements:\n1. Provide accurate timestamps for each segment (Format: MM:SS).\n2. Detect the primary language of each segment.\n3. If the segment is in a language different than English, also provide the English translation.\n4. Identify the primary emotion of the speaker in this segment. You MUST choose exactly one of the following: Happy, Sad, Angry, Neutral.\n5. Provide a brief summary of the entire audio at the beginning."
          }
        ]
      }
    ],
    "generation_config": {
      "response_mime_type": "application/json",
      "response_schema": {
        "type": "OBJECT",
        "properties": {
          "summary": {
            "type": "STRING",
            "description": "A concise summary of the audio content."
          },
          "segments": {
            "type": "ARRAY",
            "items": {
              "type": "OBJECT",
              "properties": {
                "timestamp": { "type": "STRING" },
                "content": { "type": "STRING" },
                "language": { "type": "STRING" },
                "language_code": { "type": "STRING" },
                "translation": { "type": "STRING" },
                "emotion": {
                  "type": "STRING",
                  "enum": ["happy", "sad", "angry", "neutral"]
                }
              },
              "required": ["timestamp", "content", "language", "language_code", "emotion"]
            }
          }
        },
        "required": ["summary", "segments"]
      }
    }
  }'
```

### 7.6 Token 计数

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:countTokens" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts":[
        {"file_data": {"mime_type": "audio/mp3", "file_uri": "your_file_uri"}}
      ]
    }]
  }'
```

---

## 8. Thinking (思考推理)

### 8.1 基本 Thinking 请求

默认启用动态 thinking，无需额外配置：

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Explain the concept of Occam'\''s Razor and provide a simple, everyday example."
          }
        ]
      }
    ]
  }'
```

### 8.2 Thought Summaries（思维摘要）

设置 `include_thoughts: true` 获取推理过程摘要：

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "What is the sum of the first 50 prime numbers?"
          }
        ]
      }
    ],
    "generationConfig": {
      "thinkingConfig": {
        "include_thoughts": true
      }
    }
  }'
```

> 响应中 `parts` 数组会包含 `thought: true`（思维摘要）和 `thought: false`（最终答案）的部分。

### 8.3 控制 Thinking Levels（Gemini 3 系列）

| Thinking Level | 说明 |
|:---|:---|
| `minimal` | 最低推理，适合聊天/高吞吐（Flash/Flash-Lite 默认） |
| `low` | 低延迟低成本，适合简单指令 |
| `medium` | 平衡模式 |
| `high` | 最大推理深度（Pro 默认，动态） |

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Provide a list of 3 famous physicists and their key contributions"
          }
        ]
      }
    ],
    "generationConfig": {
      "thinkingConfig": {
        "thinkingLevel": "low"
      }
    }
  }'
```

### 8.4 Thinking Budget（Gemini 2.5 系列）

| 设置 | 含义 |
|:---|:---|
| `thinkingBudget: -1` | 动态 thinking（默认） |
| `thinkingBudget: 0` | 关闭 thinking（仅部分模型支持） |
| `thinkingBudget: 1024` | 固定 1024 个 thinking token |

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Provide a list of 3 famous physicists and their key contributions"
          }
        ]
      }
    ],
    "generationConfig": {
      "thinkingConfig": {
        "thinkingBudget": 1024
      }
    }
  }'
```

---

## 9. GenerationConfig 参数详解

```json
{
  "generationConfig": {
    "temperature": 1.0,
    "topP": 0.95,
    "topK": 40,
    "maxOutputTokens": 8192,
    "stopSequences": ["END"],
    "response_mime_type": "text/plain",
    "response_schema": { ... },
    "candidateCount": 1,
    "presencePenalty": 0.0,
    "frequencyPenalty": 0.0,
    "thinkingConfig": {
      "thinkingLevel": "high",
      "include_thoughts": false,
      "thinkingBudget": -1
    },
    "media_resolution": "MEDIUM"
  }
}
```

| 参数 | 类型 | 说明 |
|:---|:---|:---|
| `temperature` | float (0-2) | 控制输出的随机性 |
| `topP` | float (0-1) | 核采样参数 |
| `topK` | int | 只从概率最高的 K 个 token 中采样 |
| `maxOutputTokens` | int | 最大输出 token 数 |
| `stopSequences` | string[] | 停止生成序列 |
| `response_mime_type` | string | `"text/plain"` 或 `"application/json"` |
| `response_schema` | object | JSON Schema（需 `response_mime_type: "application/json"`） |
| `candidateCount` | int | 候选响应数量 |
| `presencePenalty` | float | 惩罚已出现的 token |
| `frequencyPenalty` | float | 惩罚高频 token |
| `thinkingConfig` | object | 推理配置 |
| `media_resolution` | string | 图片/视频帧的 token 分配量 |

---

## 10. File API 文件上传

### 通用可恢复上传流程

**Step 1: 初始化上传**

```bash
FILE_PATH="path/to/file"
MIME_TYPE=$(file -b --mime-type "${FILE_PATH}")
NUM_BYTES=$(wc -c < "${FILE_PATH}")
DISPLAY_NAME="MyFile"

curl "https://generativelanguage.googleapis.com/upload/v1beta/files" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -D upload-header.tmp \
  -H "X-Goog-Upload-Protocol: resumable" \
  -H "X-Goog-Upload-Command: start" \
  -H "X-Goog-Upload-Header-Content-Length: ${NUM_BYTES}" \
  -H "X-Goog-Upload-Header-Content-Type: ${MIME_TYPE}" \
  -H "Content-Type: application/json" \
  -d "{'file': {'display_name': '${DISPLAY_NAME}'}}"
```

**Step 2: 上传数据**

```bash
upload_url=$(grep -i "x-goog-upload-url: " upload-header.tmp | cut -d" " -f2 | tr -d "\r")

curl "${upload_url}" \
  -H "Content-Length: ${NUM_BYTES}" \
  -H "X-Goog-Upload-Offset: 0" \
  -H "X-Goog-Upload-Command: upload, finalize" \
  --data-binary "@${FILE_PATH}" > file_info.json

file_uri=$(jq -r ".file.uri" file_info.json)
echo "File URI: ${file_uri}"
```

**Step 3: 在 GenerateContent 中使用**

```json
{
  "contents": [{
    "parts":[
      {"text": "Your prompt here"},
      {"file_data": {"mime_type": "MIME_TYPE", "file_uri": "FILE_URI"}}
    ]
  }]
}
```

### 文件输入方式对比

| 方式 | 最大大小 | 适用场景 |
|:---|:---|:---|
| **内联 (Inline Data)** | < 20MB（总请求） | 小文件、一次性使用 |
| **File API 上传** | 2GB（免费）/ 20GB（付费） | 大文件、重复使用 |
| **YouTube URL** | N/A | 公开 YouTube 视频 |
| **Cloud Storage** | 2GB/文件 | 持久化存储 |

---

## 11. 附录：支持格式与限制

### 图片格式

| MIME 类型 | 格式 |
|:---|:---|
| `image/png` | PNG |
| `image/jpeg` | JPEG |
| `image/webp` | WebP |
| `image/heic` | HEIC |
| `image/heif` | HEIF |

> 每请求最多 3,600 张图片。

### 视频格式

| MIME 类型 | 格式 |
|:---|:---|
| `video/mp4` | MP4 |
| `video/mpeg` | MPEG |
| `video/mov` | QuickTime |
| `video/avi` | AVI |
| `video/x-flv` | FLV |
| `video/mpg` | MPG |
| `video/webm` | WebM |
| `video/wmv` | WMV |
| `video/3gpp` | 3GPP |

### 音频格式

| MIME 类型 | 格式 |
|:---|:---|
| `audio/wav` | WAV |
| `audio/mp3` | MP3 |
| `audio/aiff` | AIFF |
| `audio/aac` | AAC |
| `audio/ogg` | OGG Vorbis |
| `audio/flac` | FLAC |

> - 每秒音频 ≈ 32 tokens（1分钟 ≈ 1920 tokens）
> - 单次请求最大音频总时长：9.5 小时
> - 音频降采样到 16 Kbps，多声道合并为单声道

### Token 计算参考

- **文本**：按词汇/字符计
- **图片**：按分辨率分块计算（每个 tile 258 tokens）
- **音频**：每秒 32 tokens
- **视频**：每秒抽取 1 帧（默认），每帧按图片方式计 token

### Media Resolution 参数

| 值 | 说明 |
|:---|:---|
| `"LOW"` | 最低分辨率，token 消耗最少 |
| `"MEDIUM"` | 中等分辨率（默认） |
| `"HIGH"` | 高分辨率，适合识别细小文本或细节 |

---

## 🔗 参考链接

- [Gemini API 官方文档](https://ai.google.dev/gemini-api/docs)
- [API 参考](https://ai.google.dev/api)
- [Gemini Cookbook](https://github.com/google-gemini/cookbook)
- [定价信息](https://ai.google.dev/gemini-api/docs/pricing)
- [获取 API Key](https://aistudio.google.com/apikey)

---
