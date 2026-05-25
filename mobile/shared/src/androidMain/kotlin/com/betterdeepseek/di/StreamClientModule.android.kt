package com.betterdeepseek.di

import com.betterdeepseek.data.api.OkHttpStreamClient
import com.betterdeepseek.data.api.StreamClient
import org.koin.core.module.Module
import org.koin.dsl.module

actual fun streamClientModule(): Module = module {
    single<StreamClient> { OkHttpStreamClient() }
}
