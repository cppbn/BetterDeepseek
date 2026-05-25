package com.betterdeepseek.presentation.component

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.betterdeepseek.data.model.Message

@Composable
fun MessageList(
    messages: List<Message>,
    isStreaming: Boolean,
    onRegenerate: () -> Unit,
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.lastIndex)
        }
    }

    if (messages.isEmpty()) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "开始新对话吧",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    } else {
        LazyColumn(
            state = listState,
            modifier = modifier
                .fillMaxSize()
                .padding(vertical = 8.dp)
        ) {
            items(
                items = messages,
                key = { it.seq }
            ) { msg ->
                MessageItem(
                    msg = msg,
                    isLastAssistant = msg == messages.lastOrNull { it.isAssistant }
                        && !isStreaming,
                    onRegenerate = if (msg == messages.lastOrNull { it.isAssistant } && !isStreaming)
                        onRegenerate else null
                )
            }
        }
    }
}
