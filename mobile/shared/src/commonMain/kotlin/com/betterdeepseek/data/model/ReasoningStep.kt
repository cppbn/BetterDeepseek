package com.betterdeepseek.data.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class ToolCallData(
    val name: String,
    val args: JsonObject = JsonObject(emptyMap()),
    val id: String? = null
)

class ReasoningStep private constructor(
    val type: StepType,
    var content: String = "",
    val toolName: String? = null,
    val toolArgs: JsonObject? = null,
    var toolResult: String? = null,
    var toolResultLoading: Boolean = false,
    val attachmentsFileId: MutableList<String> = mutableListOf(),
    val attachments: MutableList<FileInfo> = mutableListOf()
) {
    companion object {
        fun thinking(content: String): ReasoningStep {
            return ReasoningStep(
                type = StepType.THINKING,
                content = content
            )
        }

        fun toolCall(toolName: String, toolArgs: JsonObject?, id: String? = null): ReasoningStep {
            return ReasoningStep(
                type = StepType.TOOL_CALL,
                toolName = toolName,
                toolArgs = toolArgs,
                toolResultLoading = true,
                content = id ?: ""
            )
        }
    }

    val isThinking: Boolean get() = type == StepType.THINKING
    val isToolCall: Boolean get() = type == StepType.TOOL_CALL
}

enum class StepType {
    THINKING,
    TOOL_CALL
}
