package com.betterdeepseek.presentation.component

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.betterdeepseek.data.model.ModelConfig

@Composable
fun ModelSelector(
    models: Map<String, ModelConfig>,
    selectedModel: String,
    onModelSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }
    val selectedConfig = models[selectedModel]
    val displayName = selectedModel
    val provider = selectedConfig?.provider ?: ""

    Row(
        modifier = modifier
            .clickable { expanded = true }
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Text(
            text = "$provider/$displayName",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(Modifier.width(4.dp))
        Text("▾", style = MaterialTheme.typography.labelSmall)

        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            models.forEach { (key, config) ->
                DropdownMenuItem(
                    text = {
                        Text(
                            text = "${config.provider}/${key}",
                            style = MaterialTheme.typography.bodySmall
                        )
                    },
                    onClick = {
                        onModelSelected(key)
                        expanded = false
                    }
                )
            }
        }
    }
}
