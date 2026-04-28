<template>
  <div ref="markdownContainer" class="markdown-body" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import katex from 'katex';
import 'highlight.js/styles/github.css';
import 'katex/dist/katex.min.css';
import texmath from 'markdown-it-texmath';

const props = defineProps<{
  content: string;
}>();

const markdownContainer = ref<HTMLDivElement | null>(null);

// 使用 Heroicons 24/outline DocumentDuplicateIcon 的路径数据
const copyIcon = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
  <path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
</svg>`;

const defaultHighlight = (str: string, lang: string) => {
  if (lang && hljs.getLanguage(lang)) {
    try {
      return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`;
    } catch (__) {}
  }
  return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
};

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: defaultHighlight,
}).use(texmath, {
  engine: katex,
  delimiters: ['brackets', 'dollar'],
  katexOptions: { throwOnError: false, output: 'html' }
});

md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  const lang = token.info.trim().split(/\s+/)[0];
  const code = token.content;
  const highlighted = options.highlight ? options.highlight(code, lang, '') : md.utils.escapeHtml(code);
  const langLabel = lang
    ? `<span class="code-lang-label">${md.utils.escapeHtml(lang)}</span>`
    : '';
  return `<div class="code-block-wrapper">
    ${langLabel}
    <button type="button" class="copy-code-btn" title="复制代码">${copyIcon}</button>
    ${highlighted}
  </div>`;
};

const renderedHtml = computed(() => {
  if (!props.content) return '';

  const safeContent = props.content.replace(
    /(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)|([^\n]\n?)(\\\[)|(\\\])(\n?[^\n])/g,
    (match, code, preOpen, openBracket, closeBracket, postClose) => {
      if (code) return code;
      if (openBracket) {
        const suffix = preOpen.endsWith('\n') ? '\n' : '\n\n';
        return `${preOpen}${suffix}\\[`;
      }
      if (closeBracket) {
        const prefix = postClose.startsWith('\n') ? '\n' : '\n\n';
        return `\\]${prefix}${postClose}`;
      }
      return match;
    }
  );

  try {
    return md.render(safeContent);
  } catch (error) {
    console.error('Markdown 渲染错误:', error);
    return `<p>${props.content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;
  }
});

function handleCopyClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  const btn = target.closest('.copy-code-btn') as HTMLButtonElement | null;
  if (!btn) return;
  const wrapper = btn.closest('.code-block-wrapper') as HTMLElement | null;
  if (!wrapper) return;
  const codeElement = wrapper.querySelector('pre code');
  if (!codeElement) return;
  const codeText = codeElement.textContent || '';

  navigator.clipboard.writeText(codeText).then(() => {
    btn.innerHTML = '已复制';
    setTimeout(() => { btn.innerHTML = copyIcon; }, 2000);
  }).catch(err => console.error('复制失败:', err));
}

onMounted(() => {
  markdownContainer.value?.addEventListener('click', handleCopyClick);
});

onUnmounted(() => {
  markdownContainer.value?.removeEventListener('click', handleCopyClick);
});
</script>

<style>
.markdown-body {
  font-size: 1rem;
  line-height: 1.6;
  color: #1f2937;
}

.markdown-body * {
  max-width: 100%;
  box-sizing: border-box;
}

.code-block-wrapper {
  position: relative;
  margin: 0.75em 0;
}

.code-lang-label {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
  color: #4b5563;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(4px);
  border: 1px solid #d1d5db;
  border-radius: 4px;
  text-transform: uppercase;
  pointer-events: none;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-code-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(4px);
  color: #4b5563;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-code-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
}

.code-block-wrapper pre {
  margin: 0;
  padding: 16px;
  padding-top: 42px;
}

.markdown-body pre {
  overflow-x: auto;
  white-space: pre;
  word-break: normal;
  background-color: #f6f8fa;
  border-radius: 6px;
}

.markdown-body code {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: #f3f4f6;
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-size: 0.875em;
}

.markdown-body table {
  display: block;
  overflow-x: auto;
  white-space: nowrap;
  border-collapse: collapse;
  margin: 1em 0;
}

.markdown-body td,
.markdown-body th {
  border: 1px solid #ddd;
  padding: 6px 12px;
}

.markdown-body img {
  max-width: 100%;
  height: auto;
}

.markdown-body .katex-display {
  margin: 0.75em 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.markdown-body .katex {
  font-size: 1.1em;
}
</style>