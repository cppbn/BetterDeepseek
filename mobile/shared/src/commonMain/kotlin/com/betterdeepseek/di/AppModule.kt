package com.betterdeepseek.di

import com.betterdeepseek.data.api.ApiClientFactory
import com.betterdeepseek.data.api.SseParser
import com.betterdeepseek.data.api.StreamClient
import com.betterdeepseek.data.repository.AuthRepository
import com.betterdeepseek.data.repository.ChatRepository
import com.betterdeepseek.data.repository.FileRepository
import com.betterdeepseek.data.repository.ModelRepository
import com.betterdeepseek.data.repository.SessionRepository
import com.betterdeepseek.data.storage.TokenStorage
import com.betterdeepseek.domain.chat.ChatViewModel
import org.koin.core.module.Module
import org.koin.dsl.module

expect fun streamClientModule(): Module

val appModule: Module = module {
    single { TokenStorage() }
    single { ApiClientFactory.create(get()) }
    single { SseParser(get()) }

    includes(streamClientModule())

    single { AuthRepository(get(), get()) }
    single { SessionRepository(get()) }
    single { ChatRepository(get(), get(), get()) }
    single { FileRepository(get()) }
    single { ModelRepository(get()) }

    single { ChatViewModel(get(), get(), get(), get()) }
}
