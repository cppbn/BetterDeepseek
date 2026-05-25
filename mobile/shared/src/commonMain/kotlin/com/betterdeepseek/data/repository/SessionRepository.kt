package com.betterdeepseek.data.repository

import com.betterdeepseek.data.model.CreateSessionResponse
import com.betterdeepseek.data.model.Session
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.post

class SessionRepository(private val client: HttpClient) {

    suspend fun list(): Result<List<Session>> {
        return apiCall {
            client.get("sessions").body<List<Session>>()
        }
    }

    suspend fun create(): Result<CreateSessionResponse> {
        return apiCall {
            client.post("sessions").body<CreateSessionResponse>()
        }
    }

    suspend fun delete(sessionId: String): Result<Unit> {
        return apiCall {
            client.delete("sessions/$sessionId")
        }
    }

    private suspend fun <T> apiCall(block: suspend () -> T): Result<T> {
        return try {
            Result.success(block())
        } catch (e: Exception) {
            Result.failure(ApiException(e.message ?: "Unknown error", e))
        }
    }
}
