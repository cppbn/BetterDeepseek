package com.betterdeepseek.data.api

import com.betterdeepseek.data.model.StreamEvent
import com.betterdeepseek.data.model.StreamEventJson
import com.betterdeepseek.data.model.ToolCallData
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsChannel
import io.ktor.utils.io.ByteReadChannel
import io.ktor.utils.io.readUTF8Line
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.jsonObject

class SseParser(
    private val httpClient: HttpClient,
    private val json: Json = Json { ignoreUnknownKeys = true; isLenient = true }
) {
    suspend fun parseStream(response: HttpResponse): Flow<StreamEvent> = flow {
        val channel: ByteReadChannel = response.bodyAsChannel()
        val buffer = StringBuilder()

        try {
            var lineCount = 0
            while (!channel.isClosedForRead) {
                val line = channel.readUTF8Line() ?: break
                lineCount++

                if (line.startsWith(":")) {
                    if (lineCount <= 3) println("[SSE] ping line")
                    continue
                }

                if (line.startsWith("data: ")) {
                    val data = line.removePrefix("data: ").trim()

                    println("[SSE] data: ${data.take(120)}")

                    if (data == "[DONE]") {
                        println("[SSE] DONE")
                        break
                    }

                    val event = try {
                        val eventJson = json.decodeFromString<StreamEventJson>(data)
                        parseStreamEvent(eventJson)
                    } catch (e: Exception) {
                        continue
                    }

                    if (event != null) {
                        emit(event)
                    }
                } else if (line.isNotBlank()) {
                    println("[SSE] non-SSE: ${line.take(200)}")
                }
            }
            println("[SSE] channel closed, total lines: $lineCount")
        } catch (e: Exception) {
            throw e
        }
    }

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
                } else {
                    null
                }
            }
        }
    }

    private fun extractString(element: JsonElement): String? {
        return try {
            json.decodeFromJsonElement<String>(element)
        } catch (e: Exception) {
            null
        }
    }
}
