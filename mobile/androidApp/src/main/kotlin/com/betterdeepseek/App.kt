package com.betterdeepseek

import android.app.Application
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.betterdeepseek.data.repository.AuthRepository
import com.betterdeepseek.data.storage.TokenStorage
import com.betterdeepseek.di.appModule
import com.betterdeepseek.domain.chat.ChatViewModel
import com.betterdeepseek.presentation.navigation.Screen
import com.betterdeepseek.presentation.screen.ChatScreen
import com.betterdeepseek.presentation.screen.LoginScreen
import com.betterdeepseek.presentation.screen.RegisterScreen
import com.betterdeepseek.presentation.theme.AppTheme
import org.koin.android.ext.koin.androidContext
import org.koin.compose.koinInject
import org.koin.core.context.startKoin

class BetterDeepseekApp : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@BetterDeepseekApp)
            modules(appModule)
        }
    }
}

@Composable
fun App() {
    val authRepository = koinInject<AuthRepository>()
    val tokenStorage = koinInject<TokenStorage>()
    val isLoggedIn by remember { mutableStateOf(tokenStorage.getToken() != null) }
    var currentScreen by remember { mutableStateOf<Screen>(if (isLoggedIn) Screen.Chat else Screen.Login) }
    val username = tokenStorage.getUsername()

    fun onLoginSuccess() {
        currentScreen = Screen.Chat
    }

    fun onLogout() {
        authRepository.logout()
        currentScreen = Screen.Login
    }

    AppTheme {
        when (val screen = currentScreen) {
            is Screen.Login -> LoginScreen(
                authRepository = authRepository,
                onNavigateToRegister = { currentScreen = Screen.Register },
                onLoginSuccess = { onLoginSuccess() }
            )

            is Screen.Register -> RegisterScreen(
                authRepository = authRepository,
                onNavigateBack = { currentScreen = Screen.Login },
                onRegisterSuccess = { onLoginSuccess() }
            )

            is Screen.Chat -> {
                val chatViewModel = koinInject<ChatViewModel>()
                ChatScreen(
                    viewModel = chatViewModel,
                    username = username,
                    onLogout = { onLogout() }
                )
            }
        }
    }
}
