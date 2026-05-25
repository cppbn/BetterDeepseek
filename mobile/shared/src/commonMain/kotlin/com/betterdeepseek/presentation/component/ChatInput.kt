package com.betterdeepseek.presentation.component

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.betterdeepseek.data.model.ModelConfig

@Composable
fun ChatInput(
    onSend: (String, Boolean, Boolean) -> Unit,
    onStop: () -> Unit,
    isStreaming: Boolean,
    models: Map<String, ModelConfig> = emptyMap(),
    selectedModel: String = "",
    onModelSelected: (String) -> Unit = {},
    onAttachFile: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    var text by remember { mutableStateOf("") }
    var enableSearch by remember { mutableStateOf(true) }
    var enableCodeExec by remember { mutableStateOf(true) }
    var modelMenuExpanded by remember { mutableStateOf(false) }

    fun send() {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return
        onSend(trimmed, enableSearch, enableCodeExec)
        text = ""
    }

    val displayModel = if (selectedModel.isNotEmpty()) selectedModel else "未选择模型"
    val modelCount = models.size

    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 8.dp, vertical = 6.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Bottom
        ) {
            if (onAttachFile != null) {
                IconButton(onClick = onAttachFile, modifier = Modifier.size(44.dp)) {
                    Icon(Icons.Default.AttachFile, contentDescription = "选择文件", modifier = Modifier.size(22.dp))
                }
            }

            TextField(
                value = text,
                onValueChange = { text = it },
                placeholder = { Text("输入消息...") },
                modifier = Modifier
                    .weight(1f)
                    .defaultMinSize(minHeight = 44.dp),
                shape = RoundedCornerShape(20.dp),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                    focusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                    unfocusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent
                ),
                maxLines = 4
            )

            Spacer(Modifier.width(4.dp))

            if (isStreaming) {
                IconButton(onClick = onStop, modifier = Modifier.size(44.dp)) {
                    Icon(Icons.Default.Close, contentDescription = "停止", tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(24.dp))
                }
            } else {
                IconButton(onClick = { send() }, enabled = text.isNotBlank(), modifier = Modifier.size(44.dp)) {
                    Icon(
                        Icons.AutoMirrored.Filled.Send, contentDescription = "发送", modifier = Modifier.size(24.dp),
                        tint = if (text.isNotBlank()) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                    )
                }
            }
        }

        Spacer(Modifier.height(4.dp))

        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            FilterChip(
                selected = enableSearch,
                onClick = { enableSearch = !enableSearch },
                label = { Text("联网搜索", style = MaterialTheme.typography.labelSmall) },
                modifier = Modifier.padding(end = 6.dp)
            )
            FilterChip(
                selected = enableCodeExec,
                onClick = { enableCodeExec = !enableCodeExec },
                label = { Text("代码执行", style = MaterialTheme.typography.labelSmall) }
            )

            Spacer(Modifier.weight(1f))

            if (modelCount > 0) {
                SuggestionChip(
                    onClick = { modelMenuExpanded = true },
                    label = {
                        Text(
                            displayModel.take(20),
                            style = MaterialTheme.typography.labelSmall,
                            maxLines = 1
                        )
                    },
                    icon = {
                        Icon(
                            Icons.Default.SmartToy,
                            contentDescription = null,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                )

                DropdownMenu(
                    expanded = modelMenuExpanded,
                    onDismissRequest = { modelMenuExpanded = false }
                ) {
                    models.forEach { (key, config) ->
                        DropdownMenuItem(
                            text = {
                                Column {
                                    Text(key, style = MaterialTheme.typography.bodySmall)
                                    Text(
                                        "${config.provider}",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            },
                            onClick = {
                                onModelSelected(key)
                                modelMenuExpanded = false
                            }
                        )
                    }
                }
            }
        }
    }
}
