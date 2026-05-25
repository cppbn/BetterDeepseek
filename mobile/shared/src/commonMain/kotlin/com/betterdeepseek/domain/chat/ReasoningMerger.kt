package com.betterdeepseek.domain.chat

import com.betterdeepseek.data.model.Message
import com.betterdeepseek.data.model.ReasoningStep
import com.betterdeepseek.data.model.ToolCallData
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject

object ReasoningMerger {

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        coerceInputValues = true
    }

    fun mergeReasoningMessages(messages: List<Message>): List<Message> {
        val result = mutableListOf<Message>()
        val group = mutableListOf<Message>()

        for (msg in messages) {
            if (msg.type in setOf("reasoning", "tool_call", "tool_result")) {
                group.add(msg)
            } else {
                if (group.isNotEmpty()) {
                    result.add(mergeReasoningGroup(group))
                    group.clear()
                }
                result.add(msg)
            }
        }

        if (group.isNotEmpty()) {
            result.add(mergeReasoningGroup(group))
        }

        return result
    }

    private fun mergeReasoningGroup(group: List<Message>): Message {
        if (group.isEmpty()) {
            return Message(0, 0, 0, "assistant", "reasoning", "")
        }

        val base = group.first()
        var mergedContent = ""
        val steps = mutableListOf<ReasoningStep>()
        val allFileIds = mutableSetOf<String>()
        val allAttachments = mutableListOf<com.betterdeepseek.data.model.FileInfo>()

        for (msg in group) {
            msg.attachmentsFileId?.let { allFileIds.addAll(it) }
            allAttachments.addAll(msg.attachments)

            when (msg.type) {
                "reasoning" -> {
                    mergedContent += msg.content
                    val lastStep = steps.lastOrNull()
                    if (lastStep != null && lastStep.isThinking) {
                        lastStep.content += msg.content
                    } else {
                        steps.add(ReasoningStep.thinking(msg.content))
                    }
                }

                "tool_call" -> {
                    val toolData = msg.toolCallData ?: parseToolCallData(msg.content)
                    val step = ReasoningStep.toolCall(
                        toolData.name,
                        toolData.args,
                        toolData.id
                    )
                    steps.add(step)
                }

                "tool_result" -> {
                    val resultContent = extractResultContent(msg.content)
                    val pendingStep = steps.findLast { it.isToolCall && it.toolResultLoading }
                    if (pendingStep != null) {
                        pendingStep.toolResult = resultContent
                        pendingStep.toolResultLoading = false

                        msg.attachmentsFileId?.let { fids ->
                            pendingStep.attachmentsFileId.addAll(fids)
                        }
                        msg.attachments.forEach { att ->
                            pendingStep.attachments.add(att)
                        }
                    }
                }
            }
        }

        val merged = Message(
            id = base.id,
            seq = base.seq,
            idx = base.idx,
            role = "assistant",
            type = "reasoning",
            content = mergedContent,
            createdAt = base.createdAt,
            attachmentsFileId = allFileIds.toList()
        )
        merged.reasoningSteps = steps.toList()
        merged.attachments = allAttachments.toList()

        return merged
    }

    private fun parseToolCallData(content: String): ToolCallData {
        return try {
            json.decodeFromString<ToolCallData>(content)
        } catch (e: Exception) {
            ToolCallData(name = "unknown", args = kotlinx.serialization.json.JsonObject(emptyMap()))
        }
    }

    private fun extractResultContent(raw: String): String {
        return try {
            val obj = json.parseToJsonElement(raw).jsonObject
            val contentElement = obj["content"]
            if (contentElement is kotlinx.serialization.json.JsonPrimitive) {
                contentElement.content
            } else {
                raw
            }
        } catch (e: Exception) {
            raw
        }
    }
}
