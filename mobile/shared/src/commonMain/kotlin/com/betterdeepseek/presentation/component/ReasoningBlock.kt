package com.betterdeepseek.presentation.component

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.betterdeepseek.data.model.ReasoningStep
import com.betterdeepseek.data.model.StepType

@Composable
fun ReasoningBlock(
    steps: List<ReasoningStep>,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { expanded = !expanded }
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "推理过程",
                style = MaterialTheme.typography.labelMedium,
                modifier = Modifier.weight(1f)
            )
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = if (expanded) "折叠" else "展开",
                modifier = Modifier.rotate(if (expanded) 90f else 0f)
            )
        }

        AnimatedVisibility(visible = expanded) {
            Column(modifier = Modifier.padding(12.dp)) {
                steps.forEach { step ->
                    when (step.type) {
                        StepType.THINKING -> {
                            Text(
                                text = step.content,
                                style = MaterialTheme.typography.bodySmall,
                                fontFamily = FontFamily.Monospace,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(vertical = 4.dp)
                            )
                        }

                        StepType.TOOL_CALL -> ToolCallStepItem(step)
                    }
                }
            }
        }
    }
}

@Composable
private fun ToolCallStepItem(step: ReasoningStep) {
    var stepExpanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color(0xFFFFF8E1)
        ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.clickable { stepExpanded = !stepExpanded }.padding(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "🔧 ${step.toolName ?: "tool"}",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color(0xFFF57F17),
                    modifier = Modifier.weight(1f)
                )

                if (step.toolResultLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(14.dp),
                        strokeWidth = 2.dp,
                        color = Color(0xFFF57F17)
                    )
                }
            }

            AnimatedVisibility(visible = stepExpanded) {
                Column {
                    val args = step.toolArgs
                    if (args != null && args.isNotEmpty()) {
                        Text(
                            text = buildString {
                                for ((key, value) in args) {
                                    val str = value.toString()
                                    if (str.length > 200) {
                                        append("$key: ${str.take(200)}...\n")
                                    } else {
                                        append("$key: $str\n")
                                    }
                                }
                            }.trimEnd(),
                            style = MaterialTheme.typography.bodySmall,
                            fontFamily = FontFamily.Monospace,
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }

                    val result = step.toolResult
                    if (!result.isNullOrBlank()) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = result.take(1000),
                            style = MaterialTheme.typography.bodySmall,
                            fontFamily = FontFamily.Monospace,
                            modifier = Modifier
                                .background(Color(0xFFE8F5E9), RoundedCornerShape(4.dp))
                                .padding(6.dp)
                        )
                    }
                }
            }
        }
    }
}
