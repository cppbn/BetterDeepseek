<template>
  <div class="markdown-body" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import katex from 'katex';
import 'highlight.js/styles/github.css';
import 'katex/dist/katex.min.css';
// @ts-ignore - markdown-it-texmath 没有类型声明
import texmath from 'markdown-it-texmath';

const props = defineProps<{
  content: string;
}>();

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, { language: lang }).value;
        return `<pre class="hljs"><code>${highlighted}</code></pre>`;
      } catch (__) {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
  }
}).use(texmath, {
  engine: katex,
  delimiters: 'brackets',
  katexOptions: {
    throwOnError: false,
    output: 'html'
  }
});

const renderedHtml = computed(() => {
  if (!props.content) return '';
  
  // 预处理：上下文安全的替换策略
  let safeContent = props.content.replace(
    // 正则分为三大组，用 | 隔开：
    // 组1: 匹配 多行代码块(```...``` 或 ~~~...~~~) 或 行内代码(`...`)
    // 组2: 匹配 \[ 及其前置字符
    // 组3: 匹配 \] 及其后置字符
    /(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)|([^\n]\n?)(\\\[)|(\\\])(\n?[^\n])/g,
    (match, code, preOpen, openBracket, closeBracket, postClose) => {
      // 1. 如果命中了代码块或行内代码，直接原样返回，绝对不修改其中的任何内容！
      if (code) return code;
      
      // 2. 如果命中了 \[
      if (openBracket) {
        // 判断前面的字符是否已经带了一个换行，补齐到双换行
        const suffix = preOpen.endsWith('\n') ? '\n' : '\n\n';
        return `${preOpen}${suffix}\\[`;
      }
      
      // 3. 如果命中了 \]
      if (closeBracket) {
        // 判断后面的字符是否已经带了一个换行，补齐到双换行
        const prefix = postClose.startsWith('\n') ? '\n' : '\n\n';
        return `\\]${prefix}${postClose}`;
      }
      
      return match;
    }
  );

  // console.log('安全预处理后的内容:', safeContent);
  try {
    return md.render(safeContent);
  } catch (error) {
    console.error('Markdown 渲染错误:', error);
    return `<p>${props.content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;
  }
});
</script>

<style>
.markdown-body {
  font-size: 1rem;
  line-height: 1.6;
  color: #1f2937;
}

/* 所有子元素默认不超出父容器 */
.markdown-body * {
  max-width: 100%;
  box-sizing: border-box;
}

/* 代码块：横向滚动，保持代码格式 */
.markdown-body pre {
  overflow-x: auto;
  white-space: pre;
  word-break: normal;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 16px;
  margin: 0.5em 0;
}

/* 行内代码：允许换行 */
.markdown-body code {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: #f3f4f6;
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-size: 0.875em;
}

/* 表格：横向滚动 */
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

/* 图片自适应 */
.markdown-body img {
  max-width: 100%;
  height: auto;
}

/* 数学公式块已有的溢出控制保留 */
.markdown-body .katex-display {
  margin: 0.75em 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.markdown-body .katex {
  font-size: 1.1em;
}
</style>