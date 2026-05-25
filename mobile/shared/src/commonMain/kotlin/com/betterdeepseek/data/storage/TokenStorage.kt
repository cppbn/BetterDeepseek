package com.betterdeepseek.data.storage

import com.russhwolf.settings.Settings

class TokenStorage {
    private val settings: Settings = Settings()

    companion object {
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USERNAME = "username"
        private const val KEY_SELECTED_MODEL = "selected_model"
        private const val KEY_BASE_URL = "base_url"
    }

    fun saveToken(token: String) {
        settings.putString(KEY_ACCESS_TOKEN, token)
    }

    fun getToken(): String? {
        val token = settings.getStringOrNull(KEY_ACCESS_TOKEN)
        return if (token.isNullOrBlank()) null else token
    }

    fun clearToken() {
        settings.remove(KEY_ACCESS_TOKEN)
    }

    fun saveUserInfo(userId: Int, username: String) {
        settings.putInt(KEY_USER_ID, userId)
        settings.putString(KEY_USERNAME, username)
    }

    fun getUserId(): Int? {
        val id = settings.getIntOrNull(KEY_USER_ID)
        return if (id != null && id > 0) id else null
    }

    fun getUsername(): String? {
        return settings.getStringOrNull(KEY_USERNAME)
    }

    fun clearUserInfo() {
        settings.remove(KEY_USER_ID)
        settings.remove(KEY_USERNAME)
    }

    fun saveSelectedModel(modelKey: String) {
        settings.putString(KEY_SELECTED_MODEL, modelKey)
    }

    fun getSelectedModel(): String? {
        return settings.getStringOrNull(KEY_SELECTED_MODEL)
    }

    fun saveBaseUrl(url: String) {
        settings.putString(KEY_BASE_URL, url)
    }

    fun getBaseUrl(): String {
        return settings.getString(KEY_BASE_URL, "https://chat.mytckrlh.top/api/")
    }

    fun clear() {
        settings.clear()
    }
}
