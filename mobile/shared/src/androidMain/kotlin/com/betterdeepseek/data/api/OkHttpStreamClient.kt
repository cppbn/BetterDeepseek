package com.betterdeepseek.data.api

import android.util.Log
import com.betterdeepseek.data.model.FileIdData
import com.betterdeepseek.data.model.StreamEvent
import com.betterdeepseek.data.model.StreamEventJson
import com.betterdeepseek.data.model.ToolCallData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class OkHttpStreamClient : StreamClient {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.MINUTES)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    override suspend fun connect(
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

        Log.d("OkHttpSSE", "Connecting to $url")

        val response = client.newCall(requestBuilder.build()).execute()

        Log.d("OkHttpSSE", "Response: ${response.code}, type=${response.body?.contentType()}")

        if (!response.isSuccessful) {
            val errorBody = response.body?.string() ?: ""
            emit(StreamEvent.Error("HTTP ${response.code}: $errorBody"))
            return@flow
        }

        val source = response.body?.source() ?: run {
            emit(StreamEvent.Error("Empty response body"))
            return@flow
        }

        var lineCount = 0
        while (!source.exhausted()) {
            val line = source.readUtf8Line() ?: break
            lineCount++

            if (line.startsWith(":")) continue

            if (line.startsWith("data: ")) {
                val data = line.removePrefix("data: ").trim()
                if (data == "[DONE]") break

                val event = try {
                    val eventJson = json.decodeFromString<StreamEventJson>(data)
                    parseEvent(eventJson)
                } catch (e: Exception) {
                    Log.w("OkHttpSSE", "Parse error: ${e.message}")
                    continue
                }
                if (event != null) emit(event)
            } else if (line.isNotBlank()) {
                Log.d("OkHttpSSE", "Non-SSE: ${line.take(200)}")
            }
        }

        Log.d("OkHttpSSE", "Stream ended, lines=$lineCount")
    }.flowOn(Dispatchers.IO)

    private fun parseEvent(event: StreamEventJson): StreamEvent? {
        return when (event.type) {
            "content" -> event.content?.let { extractString(it) }?.let { StreamEvent.Content(it) }
            "reasoning_content" -> event.content?.let { extractString(it) }?.let { StreamEvent.ReasoningContent(it) }
            "tool_call" -> event.content?.let {
                try { StreamEvent.ToolCall(json.decodeFromJsonElement(ToolCallData.serializer(), it)) }
                catch (_: Exception) { null }
            }
            "tool_result" -> event.content?.let { extractString(it) }?.let { StreamEvent.ToolResult(it) }
            "file" -> event.content?.jsonObject?.get("file_id")?.let { extractString(it) }?.let {
                StreamEvent.File(FileIdData(it))
            }
            "title" -> event.content?.let { extractString(it) }?.let { StreamEvent.Title(it) }
            else -> event.error?.let { StreamEvent.Error(it) }
        }
    }

    private fun extractString(element: kotlinx.serialization.json.JsonElement): String? {
        return if (element is kotlinx.serialization.json.JsonPrimitive) element.content else null
    }
}
