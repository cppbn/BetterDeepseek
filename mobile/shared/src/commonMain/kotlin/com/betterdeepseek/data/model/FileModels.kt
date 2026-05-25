package com.betterdeepseek.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class FileUploadResponse(
    @SerialName("file_id") val fileId: String,
    @SerialName("original_filename") val originalFilename: String,
    @SerialName("file_size") val fileSize: Long
)

@Serializable
data class FileInfo(
    @SerialName("file_id") val fileId: String,
    @SerialName("original_filename") val originalFilename: String? = null,
    @SerialName("file_size") val fileSize: Long? = null,
    @SerialName("mime_type") val mimeType: String? = null
)

@Serializable
data class ChunkedUploadResponse(
    @SerialName("chunk_index") val chunkIndex: Int? = null,
    val received: Boolean? = null,
    @SerialName("file_id") val fileId: String? = null,
    @SerialName("original_filename") val originalFilename: String? = null,
    @SerialName("file_size") val fileSize: Long? = null
)

@Serializable
data class ChunkProgress(
    @SerialName("chunk_index") val chunkIndex: Int,
    val received: Boolean
)
