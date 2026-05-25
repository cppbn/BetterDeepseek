package com.betterdeepseek.data.api

import com.betterdeepseek.data.model.StreamEvent
import com.betterdeepseek.data.model.StreamEventJson
import com.betterdeepseek.data.model.ToolCallData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.jsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class OkHttpSseParser(
    private val json: Json = Json { ignoreUnknownKeys = true; isLenient = true }
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.MINUTES)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    fun parseStream(
        url: String,
        requestBody: String,
        authToken: String?
    ): Flow<StreamEvent> = flow {
        val body = requestBody.toRequestBody("application/json".toMediaType())
        val requestBuilder = Request.Builder()
            .url(url)
            .post(body)
            .header("User-Agent", "Mozilla/5.0")
            .header("Accept", "*/*")

        if (!authToken.isNullOrBlank()) {
            requestBuilder.header("Authorization", "Bearer $authToken")
        }

        val request = requestBuilder.build()

        println("[OkHttpSSE] Connecting to $url")

        val response = client.newCall(request).execute()
        val responseBody = response.body ?: run {
            println("[OkHttpSSE] Empty response body, code=${response.code}")
            if (!response.isSuccessful) {
                emit(StreamEvent.Error("HTTP ${response.code}: ${response.message}"))
            }
            return@flow
        }

        if (!response.isSuccessful) {
            println("[OkHttpSSE] Error response: ${response.code}")
            emit(StreamEvent.Error("HTTP ${response.code}: ${responseBody.string()}"))
            return@flow
        }

        println("[OkHttpSSE] Connected, code=${response.code}, type=${responseBody.contentType()}")

        val source = responseBody.source()

        while (!source.exhausted()) {
            val line = source.readUtf8Line() ?: break

            if (line.startsWith(":")) {
                continue
            }

            if (line.startsWith("data: ")) {
                val data = line.removePrefix("data: ").trim()

                if (data == "[DONE]") {
                    println("[OkHttpSSE] DONE received")
                    break
                }

                val event = try {
                    val eventJson = json.decodeFromString<StreamEventJson>(data)
                    parseStreamEvent(eventJson)
                } catch (e: Exception) {
                    println("[OkHttpSSE] Parse error: ${e.message} for data: ${data.take(100)}")
                    continue
                }

                if (event != null) {
                    emit(event)
                }
            } else if (line.isNotBlank()) {
                println("[OkHttpSSE] Non-SSE line: ${line.take(200)}")
            }
        }

        println("[OkHttpSSE] Stream ended")
    }.flowOn(Dispatchers.IO)

    private fun parseStreamEvent(event: StreamEventJson): StreamEvent? {
        val type = event.type ?: return null

        return when (type) {
            "content" -> {
                val content = event.content?.let { extractString(it) } ?: return null
                StreamEvent.Content(content)
            }
            "reasoning_content" -> {
                val content = event.content?.let { extractString(it) } ?: return null
                StreamEvent.ReasoningContent(content)
            }
            "tool_call" -> {
                val content = event.content ?: return null
                val toolCall = try {
                    json.decodeFromJsonElement<ToolCallData>(content)
                } catch (e: Exception) {
                    return null
                }
                StreamEvent.ToolCall(toolCall)
            }
            "tool_result" -> {
                val content = event.content?.let { extractString(it) } ?: return null
                StreamEvent.ToolResult(content)
            }
            "file" -> {
                val content = event.content?.jsonObject ?: return null
                val fileId = content["file_id"]?.let { extractString(it) } ?: return null
                StreamEvent.File(com.betterdeepseek.data.model.FileIdData(fileId))
            }
            "title" -> {
                val content = event.content?.let { extractString(it) } ?: return null
                StreamEvent.Title(content)
            }
            else -> {
                if (event.error != null) {
                    StreamEvent.Error(event.error)
                } else null
            }
        }
    }

    private fun extractString(element: kotlinx.serialization.json.JsonElement): String? {
        return try {
            json.decodeFromJsonElement<String>(element)
        } catch (e: Exception) {
            null
        }
    }
}
