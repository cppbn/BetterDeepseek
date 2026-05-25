package com.betterdeepseek.domain.chat

import com.betterdeepseek.data.model.ChatRequest
import com.betterdeepseek.data.model.FileInfo
import com.betterdeepseek.data.model.Message
import com.betterdeepseek.data.model.ModelConfig
import com.betterdeepseek.data.model.ReasoningStep
import com.betterdeepseek.data.model.Session
import com.betterdeepseek.data.model.StreamEvent
import com.betterdeepseek.data.repository.ChatRepository
import com.betterdeepseek.data.repository.FileRepository
import com.betterdeepseek.data.repository.ModelRepository
import com.betterdeepseek.data.repository.SessionRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

data class ChatState(
    val sessions: List<Session> = emptyList(),
    val currentSessionId: String? = null,
    val messages: List<Message> = emptyList(),
    val isStreaming: Boolean = false,
    val models: Map<String, ModelConfig> = emptyMap(),
    val selectedModel: String = "",
    val isLoadingSessions: Boolean = false,
    val isLoadingMessages: Boolean = false,
    val error: String? = null
)

data class SelectedFile(
    val tempId: String,
    val fileId: String? = null,
    val originalFilename: String,
    val fileSize: Long? = null,
    val progress: Float = 0f
)

@OptIn(ExperimentalUuidApi::class)
class ChatViewModel(
    private val sessionRepository: SessionRepository,
    private val chatRepository: ChatRepository,
    private val modelRepository: ModelRepository,
    private val fileRepository: FileRepository
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    private val _state = MutableStateFlow(ChatState())
    val state: StateFlow<ChatState> = _state.asStateFlow()

    private val _selectedFiles = MutableStateFlow<List<SelectedFile>>(emptyList())
    val selectedFiles: StateFlow<List<SelectedFile>> = _selectedFiles.asStateFlow()

    private var streamingJob: Job? = null
    private var tempIdCounter = -1L

    val isStreaming: Boolean get() = _state.value.isStreaming

    fun init() {
        println("[VM] init called")
        fetchModels()
        fetchSessions()
    }

    fun onDestroy() {
        scope.cancel()
    }

    fun setModel(modelKey: String) {
        _state.update { it.copy(selectedModel = modelKey) }
    }

    private fun generateTempId(): Long = tempIdCounter--
    private fun now(): String = kotlinx.datetime.Clock.System.now().toString()

    fun fetchModels() {
        scope.launch {
            modelRepository.getModels().onSuccess { models ->
                println("[VM] Models loaded: ${models.size}")
                _state.update { it.copy(models = models) }
                if (_state.value.selectedModel.isEmpty()) {
                    val defaultKey = models.entries
                        .find { it.value.isDefault }?.key
                        ?: models.keys.firstOrNull()
                    println("[VM] Default model: $defaultKey")
                    if (defaultKey != null) {
                        _state.update { it.copy(selectedModel = defaultKey) }
                    }
                }
            }.onFailure { e ->
                println("[VM] Models failed: ${e.message}")
            }
        }
    }

    fun fetchSessions() {
        scope.launch {
            _state.update { it.copy(isLoadingSessions = true) }
            sessionRepository.list().onSuccess { sessions ->
                _state.update { it.copy(sessions = sessions, isLoadingSessions = false) }
                val currentId = _state.value.currentSessionId
                if (currentId == null && sessions.isNotEmpty()) {
                    selectSession(sessions.first().sessionId)
                }
            }.onFailure { e ->
                _state.update { it.copy(isLoadingSessions = false, error = e.message) }
            }
        }
    }

    fun createSession() {
        scope.launch {
            sessionRepository.create().onSuccess { resp ->
                fetchSessions()
                selectSession(resp.sessionId)
            }.onFailure { e ->
                _state.update { it.copy(error = e.message) }
            }
        }
    }

    fun deleteSession(sessionId: String) {
        scope.launch {
            sessionRepository.delete(sessionId).onSuccess {
                val sessions = _state.value.sessions.filter { it.sessionId != sessionId }
                _state.update {
                    it.copy(
                        sessions = sessions,
                        currentSessionId = if (_state.value.currentSessionId == sessionId)
                            sessions.firstOrNull()?.sessionId else _state.value.currentSessionId,
                        messages = if (_state.value.currentSessionId == sessionId)
                            emptyList() else _state.value.messages
                    )
                }
                fetchSessions()
            }.onFailure { e ->
                _state.update { it.copy(error = e.message) }
            }
        }
    }

    fun selectSession(sessionId: String) {
        if (_state.value.currentSessionId == sessionId) return
        _state.update { it.copy(currentSessionId = sessionId, messages = emptyList()) }
        fetchMessages(sessionId)
    }

    fun fetchMessages(sessionId: String) {
        scope.launch {
            _state.update { it.copy(isLoadingMessages = true) }
            chatRepository.fetchMessages(sessionId).onSuccess { messages ->
                val merged = ReasoningMerger.mergeReasoningMessages(messages)
                _state.update { it.copy(messages = merged, isLoadingMessages = false) }
            }.onFailure { e ->
                _state.update { it.copy(isLoadingMessages = false, error = e.message) }
            }
        }
    }

    fun sendMessage(
        text: String,
        fileIds: List<String> = emptyList(),
        enableSearch: Boolean = true,
        enableCodeExec: Boolean = true
    ) {
        if (isStreaming) return

        val sid = _state.value.currentSessionId
        if (sid == null) {
            scope.launch {
                sessionRepository.create().onSuccess { resp ->
                    _state.update { it.copy(currentSessionId = resp.sessionId) }
                    fetchSessions()
                    doSendMessage(resp.sessionId, text, fileIds, enableSearch, enableCodeExec)
                }.onFailure { e ->
                    _state.update { it.copy(error = "创建会话失败: ${e.message}") }
                }
            }
        } else {
            doSendMessage(sid, text, fileIds, enableSearch, enableCodeExec)
        }
    }

    private fun doSendMessage(
        sessionId: String,
        text: String,
        fileIds: List<String>,
        enableSearch: Boolean,
        enableCodeExec: Boolean
    ) {
        scope.launch {
            val userMsgIdx = (_state.value.messages.lastOrNull()?.idx ?: -1) + 1
            val turnIdx = userMsgIdx + 1

            val userId = generateTempId()
            val assistantId = generateTempId()

            val userMsg = createMessage(
                id = userId, idx = userMsgIdx,
                role = "user", type = "message", content = text,
                attachmentsFileId = fileIds.ifEmpty { null }
            )

            val assistantMsg = createMessage(
                id = assistantId, idx = turnIdx,
                role = "assistant", type = "reasoning", content = ""
            ).apply { isStreaming = true }

            appendMessages(listOf(userMsg, assistantMsg))
            _state.update { it.copy(isStreaming = true) }
            _selectedFiles.value = emptyList()

            val request = ChatRequest(
                message = text,
                attachmentsFileId = fileIds.ifEmpty { null }.let { if (it.isNullOrEmpty()) null else it },
                model = _state.value.selectedModel.ifEmpty {
                    _state.value.models.keys.firstOrNull()
                },
                enableSearch = enableSearch,
                enableCodeExec = enableCodeExec
            )

            streamingJob = launch {
                println("[VM] Starting stream for session $sessionId")
                try {
                    chatRepository.streamChat(sessionId, request)
                        .onSuccess { eventFlow ->
                            println("[VM] Stream connected, collecting events")
                            eventFlow.collectLatest { event ->
                                handleStreamEvent(sessionId, turnIdx, event)
                            }
                        }
                        .onFailure { e ->
                            println("[VM] Stream failed: ${e.message}")
                            appendToLastMessage("\n\nError: ${e.message}")
                        }
                } catch (e: kotlinx.coroutines.CancellationException) {
                    println("[VM] Stream cancelled")
                    appendToLastMessage("\n（已停止）")
                    throw e
                } finally {
                    println("[VM] Stream finished")
                    finishStream(sessionId)
                }
            }
        }
    }

    fun stop() {
        streamingJob?.cancel()
        streamingJob = null
    }

    fun regenerate() {
        val sessionId = _state.value.currentSessionId ?: return
        if (isStreaming) return

        val lastUserMsg = _state.value.messages.findLast { it.isUser } ?: return

        scope.launch {
            chatRepository.deleteMessage(
                sessionId, lastUserMsg.id, keepUserFiles = true
            ).onSuccess {
                sendMessage(
                    text = lastUserMsg.content,
                    fileIds = lastUserMsg.attachmentsFileId ?: emptyList()
                )
            }.onFailure { e ->
                _state.update { it.copy(error = "Regenerate failed: ${e.message}") }
            }
        }
    }

    fun deleteMessage(messageId: Long) {
        val sessionId = _state.value.currentSessionId ?: return
        scope.launch {
            chatRepository.deleteMessage(sessionId, messageId).onSuccess {
                fetchMessages(sessionId)
            }.onFailure { e ->
                _state.update { it.copy(error = "Delete failed: ${e.message}") }
            }
        }
    }

    fun addFile(fileName: String, fileBytes: ByteArray, mimeType: String = "application/octet-stream") {
        val tempId = kotlin.uuid.Uuid.random().toString()
        val sessionId = _state.value.currentSessionId ?: return

        _selectedFiles.update { it + SelectedFile(tempId = tempId, originalFilename = fileName,
            fileSize = fileBytes.size.toLong(), progress = 0f) }

        scope.launch {
            val result = if (fileBytes.size > 1024 * 1024) {
                uploadChunked(sessionId, tempId, fileName, fileBytes, mimeType)
            } else {
                fileRepository.upload(sessionId, fileName, fileBytes, mimeType)
            }

            result.onSuccess { resp ->
                _selectedFiles.update { files ->
                    files.map { f -> if (f.tempId == tempId) f.copy(fileId = resp.fileId, progress = 1f) else f }
                }
            }.onFailure {
                _selectedFiles.update { files -> files.filter { f -> f.tempId != tempId } }
            }
        }
    }

    fun removeFile(tempId: String) {
        _selectedFiles.update { it.filter { f -> f.tempId != tempId } }
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }

    private suspend fun uploadChunked(
        sessionId: String, tempId: String, fileName: String,
        fileBytes: ByteArray, mimeType: String
    ): Result<com.betterdeepseek.data.model.FileUploadResponse> {
        val chunkSize = 256 * 1024
        val totalChunks = (fileBytes.size + chunkSize - 1) / chunkSize
        var lastResult: Result<com.betterdeepseek.data.model.FileUploadResponse> =
            Result.failure(Exception("No chunks uploaded"))

        for (i in 0 until totalChunks) {
            val offset = i * chunkSize
            val end = minOf(offset + chunkSize, fileBytes.size)
            val chunk = fileBytes.copyOfRange(offset, end)

            val result = fileRepository.uploadChunked(
                sessionId = sessionId, fileId = tempId, chunkIndex = i,
                totalChunks = totalChunks, fileName = fileName,
                chunkBytes = chunk, mimeType = mimeType,
                onProgress = { pct ->
                    _selectedFiles.update { files ->
                        files.map { f -> if (f.tempId == tempId) f.copy(progress = pct) else f }
                    }
                }
            )

            if (result.isFailure) return result
            lastResult = result
        }
        return lastResult
    }

    private fun createMessage(
        id: Long, idx: Int, role: String, type: String, content: String,
        attachmentsFileId: List<String>? = null
    ): Message {
        return Message(
            id = id, seq = 0, idx = idx,
            role = role, type = type, content = content,
            createdAt = now(), attachmentsFileId = attachmentsFileId
        )
    }

    private fun appendMessages(newMessages: List<Message>) {
        _state.update { state ->
            val list = state.messages.toMutableList()
            for (msg in newMessages) {
                val seq = (list.lastOrNull()?.seq ?: -1) + 1
                val copy = msg.copy(seq = seq)
                copyBody(copy, msg)
                list.add(copy)
            }
            state.copy(messages = list)
        }
    }

    private fun updateLastMessage(transform: (Message) -> Message) {
        _state.update { state ->
            val messages = state.messages.toMutableList()
            if (messages.isNotEmpty()) {
                val prev = messages.last()
                val next = transform(prev)
                messages[messages.lastIndex] = next
            }
            state.copy(messages = messages)
        }
    }

    private fun appendToLastMessage(text: String) {
        updateLastMessage { msg ->
            val next = msg.copy(content = msg.content + text)
            copyBody(next, msg)
            next
        }
    }

    private fun handleStreamEvent(sessionId: String, turnIdx: Int, event: StreamEvent) {
        when (event) {
            is StreamEvent.Content -> handleContent(turnIdx, event.content)
            is StreamEvent.ReasoningContent -> handleReasoningContent(turnIdx, event.content)
            is StreamEvent.ToolCall -> handleToolCall(turnIdx, event.content)
            is StreamEvent.ToolResult -> handleToolResult(event.content)
            is StreamEvent.File -> handleFileEvent(event.content.fileId)
            is StreamEvent.Error -> {
                appendToLastMessage("\n\n${event.error}")
                updateLastMessage { msg ->
                    val next = msg.copy(content = msg.content)
                    copyBody(next, msg)
                    next.isStreaming = false
                    next
                }
            }
            is StreamEvent.Title -> updateSessionTitle(sessionId, event.content)
        }
    }

    private fun handleContent(turnIdx: Int, content: String) {
        updateLastMessage { msg ->
            if (msg.type == "reasoning") {
                val next = msg.copy(type = "message", role = "assistant", content = content, idx = turnIdx)
                copyBody(next, msg)
                next.isStreaming = true
                next
            } else {
                val next = msg.copy(content = msg.content + content)
                copyBody(next, msg)
                next.isStreaming = true
                next
            }
        }
    }

    private fun handleReasoningContent(turnIdx: Int, content: String) {
        updateLastMessage { msg ->
            if (msg.type != "reasoning") {
                val next = createMessage(
                    id = generateTempId(), idx = turnIdx,
                    role = "assistant", type = "reasoning", content = content
                ).apply {
                    isStreaming = true
                    reasoningSteps = listOf(ReasoningStep.thinking(content))
                }
                next
            } else {
                val steps = msg.reasoningSteps.toMutableList()
                val lastStep = steps.lastOrNull()
                if (lastStep != null && lastStep.isThinking) {
                    lastStep.content += content
                } else {
                    steps.add(ReasoningStep.thinking(content))
                }
                val next = msg.copy(content = msg.content + content)
                copyBody(next, msg)
                next.isStreaming = true
                next.reasoningSteps = steps.toList()
                next
            }
        }
    }

    private fun handleToolCall(turnIdx: Int, toolCallData: com.betterdeepseek.data.model.ToolCallData) {
        updateLastMessage { msg ->
            val step = ReasoningStep.toolCall(toolCallData.name, toolCallData.args, toolCallData.id)

            if (msg.type == "reasoning") {
                val steps = msg.reasoningSteps.toMutableList()
                steps.add(step)
                val next = msg.copy(content = msg.content)
                copyBody(next, msg)
                next.isStreaming = true
                next.reasoningSteps = steps.toList()
                next
            } else {
                val next = createMessage(
                    id = generateTempId(), idx = turnIdx,
                    role = "assistant", type = "tool_call", content = toolCallData.name
                ).apply {
                    this.toolCallData = toolCallData
                    isStreaming = true
                }
                next
            }
        }
    }

    private fun handleToolResult(result: String) {
        updateLastMessage { msg ->
            if (msg.type == "reasoning") {
                val steps = msg.reasoningSteps.toMutableList()
                val pendingIdx = steps.indexOfLast { it.isToolCall && it.toolResultLoading }
                if (pendingIdx >= 0) {
                    steps[pendingIdx].toolResult = result
                    steps[pendingIdx].toolResultLoading = false
                }
                val next = msg.copy(content = msg.content)
                copyBody(next, msg)
                next.isStreaming = true
                next.reasoningSteps = steps.toList()
                next
            } else {
                val next = createMessage(
                    id = generateTempId(), idx = msg.idx,
                    role = "tool", type = "tool_result", content = result
                )
                next
            }
        }
    }

    private fun handleFileEvent(fileId: String) {
        updateLastMessage { msg ->
            if (msg.type == "reasoning") {
                val steps = msg.reasoningSteps.toMutableList()
                val pendingIdx = steps.indexOfLast { it.isToolCall && it.toolResultLoading }
                if (pendingIdx >= 0) {
                    steps[pendingIdx].attachmentsFileId.add(fileId)
                }
                val fids = msg.attachmentsFileId?.toMutableList() ?: mutableListOf()
                if (!fids.contains(fileId)) fids.add(fileId)
                val next = msg.copy(attachmentsFileId = fids.toList(), content = msg.content)
                copyBody(next, msg)
                next.isStreaming = true
                next.reasoningSteps = steps.toList()
                next
            } else {
                val next = msg.copy(content = msg.content)
                copyBody(next, msg)
                next.isStreaming = true
                next
            }
        }
        fetchFileInfo(fileId)
    }

    private fun fetchFileInfo(fileId: String) {
        val sessionId = _state.value.currentSessionId ?: return
        scope.launch {
            fileRepository.getMetadata(sessionId, fileId).onSuccess { fileInfo ->
                updateLastMessage { msg ->
                    val attachments = msg.attachments.toMutableList()
                    if (attachments.none { it.fileId == fileId }) attachments.add(fileInfo)
                    val next = msg.copy(content = msg.content)
                    copyBody(next, msg)
                    next.attachments = attachments.toList()
                    next
                }
            }
        }
    }

    private fun updateSessionTitle(sessionId: String, title: String) {
        _state.update { state ->
            state.copy(sessions = state.sessions.map {
                if (it.sessionId == sessionId) it.copy(title = title) else it
            })
        }
    }

    private fun finishStream(sessionId: String) {
        updateLastMessage { msg ->
            val next = msg.copy(content = msg.content)
            copyBody(next, msg)
            next.isStreaming = false
            next
        }
        _state.update { it.copy(isStreaming = false) }
        syncAfterStream(sessionId)
    }

    private fun syncAfterStream(sessionId: String) {
        scope.launch {
            chatRepository.fetchMessages(sessionId).onSuccess { messages ->
                val merged = ReasoningMerger.mergeReasoningMessages(messages)
                _state.update { it.copy(messages = merged) }
            }
        }
    }

    private fun copyBody(target: Message, source: Message) {
        target.isStreaming = source.isStreaming
        target.reasoningSteps = source.reasoningSteps
        target.attachments = source.attachments
        target.toolCallData = source.toolCallData
    }
}
