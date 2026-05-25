package com.betterdeepseek.presentation.navigation

sealed class Screen {
    data object Login : Screen()
    data object Register : Screen()
    data object Chat : Screen()
}
