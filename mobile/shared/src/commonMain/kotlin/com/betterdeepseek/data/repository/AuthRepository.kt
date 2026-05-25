package com.betterdeepseek.data.repository

import com.betterdeepseek.data.model.LoginRequest
import com.betterdeepseek.data.model.RegisterRequest
import com.betterdeepseek.data.model.TokenResponse
import com.betterdeepseek.data.model.User
import com.betterdeepseek.data.storage.TokenStorage
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class AuthRepository(
    private val client: HttpClient,
    private val tokenStorage: TokenStorage
) {
    suspend fun login(username: String, password: String): Result<TokenResponse> {
        return apiCall {
            val response = client.post("login") {
                contentType(ContentType.Application.Json)
                setBody(LoginRequest(username, password))
            }
            response.body<TokenResponse>()
        }
    }

    suspend fun register(username: String, password: String): Result<TokenResponse> {
        return apiCall {
            val response = client.post("register") {
                contentType(ContentType.Application.Json)
                setBody(RegisterRequest(username, password))
            }
            response.body<TokenResponse>()
        }
    }

    suspend fun getMe(): Result<User> {
        return apiCall {
            val response = client.get("me")
            response.body<User>()
        }
    }

    fun saveTokenOnly(token: String) {
        tokenStorage.saveToken(token)
    }

    fun saveTokenAndUser(tokenResponse: TokenResponse, user: User) {
        tokenStorage.saveToken(tokenResponse.accessToken)
        tokenStorage.saveUserInfo(user.id, user.username)
    }

    fun logout() {
        tokenStorage.clear()
    }

    private suspend fun <T> apiCall(block: suspend () -> T): Result<T> {
        return try {
            Result.success(block())
        } catch (e: Exception) {
            val errorMsg = extractErrorMessage(e)
            if (errorMsg.contains("401") || errorMsg.contains("Invalid or Expired Token")) {
                logout()
            }
            Result.failure(ApiException(errorMsg, e))
        }
    }

    private fun extractErrorMessage(e: Exception): String {
        return try {
            val cause = e.cause
            cause?.message ?: e.message ?: "Unknown error"
        } catch (_: Exception) {
            e.message ?: "Unknown error"
        }
    }
}

class ApiException(message: String, cause: Throwable? = null) : Exception(message, cause)
