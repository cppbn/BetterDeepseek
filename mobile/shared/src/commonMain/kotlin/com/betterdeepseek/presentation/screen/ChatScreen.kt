package com.betterdeepseek.presentation.screen

import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import com.betterdeepseek.domain.chat.ChatViewModel
import com.betterdeepseek.presentation.component.ChatInput
import com.betterdeepseek.presentation.component.MessageList
import com.betterdeepseek.presentation.component.SessionDrawer
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    viewModel: ChatViewModel,
    username: String?,
    onLogout: () -> Unit
) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        viewModel.init()
    }

    LaunchedEffect(state.error) {
        state.error?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearError()
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                SessionDrawer(
                    sessions = state.sessions,
                    currentSessionId = state.currentSessionId,
                    username = username,
                    onSelectSession = { id ->
                        viewModel.selectSession(id)
                        scope.launch { drawerState.close() }
                    },
                    onDeleteSession = { id ->
                        viewModel.deleteSession(id)
                    },
                    onCreateSession = {
                        viewModel.createSession()
                        scope.launch { drawerState.close() }
                    },
                    onLogout = onLogout
                )
            }
        }
    ) {
        Scaffold(
            modifier = Modifier.imePadding(),
            snackbarHost = { SnackbarHost(snackbarHostState) },
            topBar = {
                TopAppBar(
                    title = {
                        Text(
                            state.sessions
                                .find { it.sessionId == state.currentSessionId }
                                ?.title ?: "BetterDeepseek"
                        )
                    },
                    navigationIcon = {
                        IconButton(onClick = {
                            scope.launch {
                                if (drawerState.isClosed) drawerState.open()
                                else drawerState.close()
                            }
                        }) {
                            Icon(Icons.Default.Menu, contentDescription = "会话列表")
                        }
                    }
                )
            },
            bottomBar = {
                ChatInput(
                    onSend = { text, enableSearch, enableCodeExec ->
                        val fileIds = viewModel.selectedFiles.value
                            .filter { it.fileId != null }
                            .map { it.fileId!! }
                        viewModel.sendMessage(text, fileIds, enableSearch, enableCodeExec)
                    },
                    onStop = { viewModel.stop() },
                    isStreaming = state.isStreaming,
                    models = state.models,
                    selectedModel = state.selectedModel,
                    onModelSelected = { viewModel.setModel(it) }
                )
            }
        ) { padding ->
            MessageList(
                messages = state.messages,
                isStreaming = state.isStreaming,
                onRegenerate = { viewModel.regenerate() },
                modifier = Modifier.padding(padding)
            )
        }
    }
}
