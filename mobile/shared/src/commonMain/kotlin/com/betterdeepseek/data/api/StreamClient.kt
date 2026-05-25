package com.betterdeepseek.data.api

import com.betterdeepseek.data.model.StreamEvent
import kotlinx.coroutines.flow.Flow

interface StreamClient {
    suspend fun connect(url: String, requestBody: String, authToken: String?): Flow<StreamEvent>
}
