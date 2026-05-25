package com.betterdeepseek.data.api

import io.ktor.client.HttpClient
import io.ktor.client.HttpClientConfig

expect fun createPlatformHttpClient(config: HttpClientConfig<*>.() -> Unit): HttpClient
