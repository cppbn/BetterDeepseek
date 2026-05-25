package com.betterdeepseek.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class TavilySearchData(
    val results: List<TavilySearchResult> = emptyList(),
    val answer: String? = null
)

@Serializable
data class TavilySearchResult(
    val title: String = "",
    val url: String = "",
    val content: String = "",
    val score: Double? = null,
    @SerialName("raw_content") val rawContent: String? = null
)

@Serializable
data class TavilyPageData(
    val results: List<TavilyPageResult> = emptyList()
)

@Serializable
data class TavilyPageResult(
    val url: String = "",
    val content: String? = null,
    @SerialName("raw_content") val rawContent: String? = null
)

@Serializable
data class TavilyMapData(
    @SerialName("base_url") val baseUrl: String = "",
    val urls: List<String> = emptyList(),
    val total: Int? = null
)
