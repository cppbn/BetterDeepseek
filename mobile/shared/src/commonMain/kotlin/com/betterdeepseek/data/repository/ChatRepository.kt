package com.betterdeepseek.data.repository

import com.betterdeepseek.data.api.StreamClient
import com.betterdeepseek.data.model.ChatRequest
import com.betterdeepseek.data.model.Message
import com.betterdeepseek.data.model.StreamEvent
import com.betterdeepseek.data.storage.TokenStorage
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.json.Json

class ChatRepository(
    private val client: HttpClient,
    private val streamClient: StreamClient,
    private val tokenStorage: TokenStorage
) {
    suspend fun streamChat(
        sessionId: String,
        request: ChatRequest
    ): Result<Flow<StreamEvent>> {
        return try {
            val body = Json {
                encodeDefaults = true
                ignoreUnknownKeys = true
            }.encodeToString(ChatRequest.serializer(), request)
            val baseUrl = tokenStorage.getBaseUrl().trimEnd('/')
            val url = "$baseUrl/sessions/$sessionId/chat/stream"
            val token = tokenStorage.getToken()
            println("[Stream] $url body=$body")
            val flow = streamClient.connect(url, body, token)
            Result.success(flow)
        } catch (e: Exception) {
            println("[Stream] Exception: ${e::class.simpleName}: ${e.message}")
            Result.failure(ApiException(e.message ?: "Stream failed", e))
        }
    }

    suspend fun fetchMessages(sessionId: String): Result<List<Message>> {
        return apiCall { client.get("sessions/$sessionId/messages").body() }
    }

    suspend fun deleteMessage(
        sessionId: String, messageId: Long, keepUserFiles: Boolean = false
    ): Result<Unit> {
        return apiCall {
            client.delete("sessions/$sessionId/messages/$messageId?keep_user_files=$keepUserFiles")
        }
    }

    private suspend fun <T> apiCall(block: suspend () -> T): Result<T> {
        return try { Result.success(block()) }
        catch (e: Exception) { Result.failure(ApiException(e.message ?: "Unknown error", e)) }
    }
}
