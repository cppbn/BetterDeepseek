package com.betterdeepseek.data.api

import com.betterdeepseek.data.storage.TokenStorage
import io.ktor.client.HttpClient
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.header
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

object ApiClientFactory {

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
        coerceInputValues = true
    }

    fun create(tokenStorage: TokenStorage): HttpClient {
        return createPlatformHttpClient {
            install(ContentNegotiation) {
                json(json)
            }

            install(Logging) {
                level = LogLevel.BODY
            }

            defaultRequest {
                url(tokenStorage.getBaseUrl())
                header(HttpHeaders.UserAgent, "curl/8.5.0")
                header(HttpHeaders.Accept, "*/*")
                val token = tokenStorage.getToken()?.trim()
                if (!token.isNullOrEmpty()) {
                    header(HttpHeaders.Authorization, "Bearer $token")
                }
            }
        }
    }
}
