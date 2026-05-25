package com.betterdeepseek.data.repository

import com.betterdeepseek.data.model.ModelConfig
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get

class ModelRepository(private val client: HttpClient) {

    suspend fun getModels(): Result<Map<String, ModelConfig>> {
        return apiCall {
            client.get("models").body<Map<String, ModelConfig>>()
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
