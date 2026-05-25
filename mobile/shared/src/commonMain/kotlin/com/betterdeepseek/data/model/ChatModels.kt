package com.betterdeepseek.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.Transient

@Serializable
data class ChatRequest(
    val message: String,
    @SerialName("attachments_file_id") val attachmentsFileId: List<String>? = null,
    val model: String? = null,
    @SerialName("enable_search") val enableSearch: Boolean = true,
    @SerialName("enable_code_exec") val enableCodeExec: Boolean = true
)

@Serializable
data class Message(
    val id: Long,
    val seq: Int = 0,
    val idx: Int = 0,
    val role: String,
    val type: String,
    val content: String,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("attachments_file_id") val attachmentsFileId: List<String>? = null
) {
    @Transient
    var isStreaming: Boolean = false

    @Transient
    var reasoningSteps: List<ReasoningStep> = emptyList()

    @Transient
    var attachments: List<FileInfo> = emptyList()

    @Transient
    var toolCallData: ToolCallData? = null

    val isUser: Boolean get() = role == "user"
    val isAssistant: Boolean get() = role == "assistant"
    val isTool: Boolean get() = role == "tool"
    val isReasoning: Boolean get() = type == "reasoning"
    val isToolCall: Boolean get() = type == "tool_call"
    val isToolResult: Boolean get() = type == "tool_result"
    val isPlainMessage: Boolean get() = type == "message"
}
