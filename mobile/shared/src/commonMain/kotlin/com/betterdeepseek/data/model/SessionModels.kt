package com.betterdeepseek.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Session(
    @SerialName("session_id") val sessionId: String,
    val title: String? = null,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class CreateSessionResponse(
    @SerialName("session_id") val sessionId: String
)

@Serializable
data class DeleteSessionResponse(
    val status: String,
    @SerialName("session_id") val sessionId: String
)

@Serializable
data class SessionListResponse(
    val sessions: List<Session>
)
