package com.betterdeepseek.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

sealed class StreamEvent {
    data class Content(val content: String) : StreamEvent()
    data class ReasoningContent(val content: String) : StreamEvent()
    data class ToolCall(val content: ToolCallData) : StreamEvent()
    data class ToolResult(val content: String) : StreamEvent()
    data class File(val content: FileIdData) : StreamEvent()
    data class Error(val error: String) : StreamEvent()
    data class Title(val content: String) : StreamEvent()
}

@Serializable
data class FileIdData(
    @SerialName("file_id") val fileId: String
)

@Serializable
data class StreamEventJson(
    val type: String? = null,
    val content: kotlinx.serialization.json.JsonElement? = null,
    val error: String? = null
)
