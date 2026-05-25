package com.betterdeepseek.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ModelConfig(
    val provider: String = "",
    val model: String = "",
    val thinking: Boolean = false,
    @SerialName("accept_image") val acceptImage: Boolean = false,
    @SerialName("accept_audio") val acceptAudio: Boolean = false,
    @SerialName("is_default") val isDefault: Boolean = false,
    val category: String = "chat"
)
