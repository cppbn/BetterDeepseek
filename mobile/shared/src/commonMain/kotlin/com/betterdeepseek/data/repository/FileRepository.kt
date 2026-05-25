package com.betterdeepseek.data.repository

import com.betterdeepseek.data.model.FileInfo
import com.betterdeepseek.data.model.FileUploadResponse
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.forms.MultiPartFormDataContent
import io.ktor.client.request.forms.formData
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.Headers
import io.ktor.http.HttpHeaders

class FileRepository(private val client: HttpClient) {

    suspend fun upload(
        sessionId: String,
        fileName: String,
        fileBytes: ByteArray,
        mimeType: String = "application/octet-stream"
    ): Result<FileUploadResponse> {
        return apiCall {
            client.post("sessions/$sessionId/files") {
                setBody(MultiPartFormDataContent(formData {
                    append("file", fileBytes, Headers.build {
                        append(HttpHeaders.ContentDisposition, "filename=\"$fileName\"")
                        append(HttpHeaders.ContentType, mimeType)
                    })
                }))
            }.body<FileUploadResponse>()
        }
    }

    suspend fun uploadChunked(
        sessionId: String,
        fileId: String,
        chunkIndex: Int,
        totalChunks: Int,
        fileName: String,
        chunkBytes: ByteArray,
        mimeType: String = "application/octet-stream",
        onProgress: ((Float) -> Unit)? = null
    ): Result<FileUploadResponse> {
        return apiCall {
            val response = client.post("sessions/$sessionId/files/chunked") {
                setBody(MultiPartFormDataContent(formData {
                    append("file_id", fileId)
                    append("chunk_index", chunkIndex.toString())
                    append("total_chunks", totalChunks.toString())
                    append("original_filename", fileName)
                    append("mime_type", mimeType)
                    append("chunk", chunkBytes, Headers.build {
                        append(HttpHeaders.ContentDisposition, "filename=\"$fileName\"")
                        append(HttpHeaders.ContentType, mimeType)
                    })
                }))
            }

            if (chunkIndex == totalChunks - 1) {
                response.body<FileUploadResponse>()
            } else {
                onProgress?.invoke((chunkIndex + 1).toFloat() / totalChunks)
                FileUploadResponse(fileId, fileName, chunkBytes.size.toLong())
            }
        }
    }

    suspend fun getMetadata(sessionId: String, fileId: String): Result<FileInfo> {
        return apiCall {
            client.get("sessions/$sessionId/files/$fileId/metadata").body<FileInfo>()
        }
    }

    suspend fun download(sessionId: String, fileId: String): Result<ByteArray> {
        return apiCall {
            client.get("sessions/$sessionId/files/$fileId").body<ByteArray>()
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
