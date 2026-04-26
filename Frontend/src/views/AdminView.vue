<template>
  <!-- 未验证：显示密钥输入 -->
  <div v-if="!verified" class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-2xl shadow-lg p-8 w-full max-w-sm">
      <h1 class="text-xl font-bold text-gray-800 text-center mb-6">管理员登录</h1>
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">管理员密钥</label>
          <input
            v-model="keyInput"
            type="password"
            placeholder="请输入 Admin API Key"
            class="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            @keyup.enter="doVerify"
          />
        </div>
        <p v-if="verifyError" class="text-red-500 text-sm">{{ verifyError }}</p>
        <button
          @click="doVerify"
          :disabled="verifying"
          class="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {{ verifying ? '验证中...' : '验证' }}
        </button>
      </div>
      <div class="mt-4 text-center">
        <router-link to="/chat" class="text-sm text-blue-600 hover:underline">返回聊天</router-link>
      </div>
    </div>
  </div>

  <!-- 已验证：管理面板 -->
  <div v-else class="min-h-screen bg-gray-50 p-6 max-w-6xl mx-auto">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold text-gray-800">管理面板</h1>
      <div class="flex items-center gap-3">
        <button @click="doLogout" class="text-sm text-gray-500 hover:text-red-500 transition">退出</button>
        <router-link to="/chat" class="text-sm text-blue-600 hover:underline">返回聊天</router-link>
      </div>
    </div>

    <!-- 标签页 -->
    <div class="flex gap-1 mb-6 border-b">
      <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
        class="px-4 py-2 text-sm rounded-t-lg transition"
        :class="activeTab === tab.id ? 'bg-white text-blue-600 font-medium shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        {{ tab.label }}
      </button>
    </div>

    <div class="bg-white rounded-xl shadow-sm p-6">

      <!-- 配置 -->
      <div v-if="activeTab === 'env'">
        <h2 class="text-lg font-semibold mb-4">API 密钥与系统提示词</h2>
        <div v-if="envLoading" class="text-gray-400">加载中...</div>
        <div v-else class="space-y-4">
          <div v-for="item in envConfigs" :key="item.key" class="border rounded-lg p-4">
            <label class="block text-sm font-medium text-gray-600 mb-1">{{ keyLabel(item.key) }}</label>
            <!-- 提示词 -->
            <template v-if="item.key.includes('PROMPT')">
              <textarea v-model="item.value"
                class="w-full border rounded px-3 py-2 text-sm font-mono resize-y" rows="6" />
            </template>
            <!-- API 密钥 -->
            <template v-else>
              <div class="flex items-center gap-2">
                <input
                  :type="revealedKeys.has(item.key) ? 'text' : 'password'"
                  :value="revealedKeys.has(item.key) ? item.value : item.value"
                  readonly
                  class="flex-1 border rounded px-3 py-2 text-sm bg-gray-50 font-mono" />
                <button @click="toggleReveal(item.key)"
                  class="px-2.5 py-1.5 text-xs border rounded-md hover:bg-gray-100 transition"
                  :title="revealedKeys.has(item.key) ? '隐藏' : '显示'">
                  {{ revealedKeys.has(item.key) ? '隐藏' : '显示' }}
                </button>
                <button @click="copyText(item.value)"
                  class="px-2.5 py-1.5 text-xs border rounded-md hover:bg-gray-100 transition"
                  title="复制">
                  复制
                </button>
              </div>
              <div class="flex items-center gap-2 mt-2">
                <input v-model="item.value"
                  type="password"
                  placeholder="输入新值以替换"
                  class="flex-1 border rounded px-3 py-2 text-sm" />
              </div>
            </template>
            <button @click="saveEnv(item)"
              class="mt-2 px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
              保存
            </button>
            <span v-if="item.saved" class="ml-2 text-green-600 text-sm">已保存</span>
          </div>
        </div>
      </div>

      <!-- 模型 -->
      <div v-if="activeTab === 'models'">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">模型配置</h2>
          <button @click="startNewModel" class="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
            + 添加模型
          </button>
        </div>
        <div v-if="modelsLoading" class="text-gray-400">加载中...</div>
        <div v-else>
          <div v-for="m in models" :key="m.key" class="border rounded-lg p-4 mb-3">
            <div class="flex items-center justify-between mb-2">
              <span class="font-medium">{{ m.key }}</span>
              <div class="flex gap-3">
                <button @click="editModel(m)" class="text-sm text-blue-600 hover:underline">编辑</button>
                <button @click="removeModel(m.key)" class="text-sm text-red-500 hover:underline">删除</button>
              </div>
            </div>
            <div class="text-xs text-gray-500 space-x-3">
              <span>提供商: {{ m.provider }}</span>
              <span>模型: {{ m.model }}</span>
              <span>分类: {{ categoryLabel(m.category) }}</span>
              <span v-if="m.thinking" class="text-blue-500">推理</span>
              <span v-if="m.accept_image" class="text-green-500">图片</span>
              <span v-if="m.accept_audio" class="text-purple-500">音频</span>
              <span v-if="m.is_default" class="text-orange-500 font-bold">默认</span>
            </div>
          </div>

          <!-- 编辑/新建弹窗 -->
          <div v-if="editingModel" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
              <h3 class="text-lg font-semibold mb-4">{{ editingModel._new ? '添加模型' : '编辑模型' }}</h3>
              <div class="space-y-3">
                <div><label class="text-xs text-gray-500">标识 Key</label>
                  <input v-model="editingModel.key" class="w-full border rounded px-3 py-1.5 text-sm"
                    :disabled="!editingModel._new" /></div>
                <div><label class="text-xs text-gray-500">提供商</label>
                  <select v-model="editingModel.provider" class="w-full border rounded px-3 py-1.5 text-sm">
                    <option>deepseek</option><option>openrouter</option>
                  </select></div>
                <div><label class="text-xs text-gray-500">模型 ID</label>
                  <input v-model="editingModel.model" class="w-full border rounded px-3 py-1.5 text-sm" /></div>
                <div><label class="text-xs text-gray-500">分类</label>
                  <select v-model="editingModel.category" class="w-full border rounded px-3 py-1.5 text-sm">
                    <option value="chat">对话</option>
                    <option value="image">图片识别</option>
                    <option value="audio">音频识别</option>
                    <option value="title">标题生成</option>
                  </select></div>
                <div class="flex gap-4 flex-wrap">
                  <label class="flex items-center gap-1 text-sm"><input type="checkbox" v-model="editingModel.thinking"> 推理模式</label>
                  <label class="flex items-center gap-1 text-sm"><input type="checkbox" v-model="editingModel.accept_image"> 支持图片</label>
                  <label class="flex items-center gap-1 text-sm"><input type="checkbox" v-model="editingModel.accept_audio"> 支持音频</label>
                  <label class="flex items-center gap-1 text-sm"><input type="checkbox" v-model="editingModel.is_default"> 设为默认</label>
                </div>
              </div>
              <div class="flex justify-end gap-2 mt-5">
                <button @click="editingModel = null" class="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">取消</button>
                <button @click="saveModel" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">保存</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 用户 -->
      <div v-if="activeTab === 'users'">
        <h2 class="text-lg font-semibold mb-4">用户管理</h2>
        <div v-if="usersLoading" class="text-gray-400">加载中...</div>
        <table v-else class="w-full text-sm">
          <thead><tr class="text-left text-gray-500 border-b">
            <th class="pb-2">ID</th><th class="pb-2">用户名</th><th class="pb-2">注册时间</th><th class="pb-2">操作</th>
          </tr></thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" class="border-b">
              <td class="py-2">{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td class="text-gray-400">{{ u.created_at }}</td>
              <td><button @click="removeUser(u.id)" class="text-red-500 hover:underline text-xs">删除</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 用量统计 -->
      <div v-if="activeTab === 'usage'">
        <h2 class="text-lg font-semibold mb-4">Token 用量统计</h2>
        <div v-if="usageLoading" class="text-gray-400">加载中...</div>
        <div v-else-if="usage">
          <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-blue-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-blue-700">{{ usage.summary.total_prompt_tokens.toLocaleString() }}</div>
              <div class="text-xs text-gray-500">输入 Token</div>
            </div>
            <div class="bg-green-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-green-700">{{ usage.summary.total_completion_tokens.toLocaleString() }}</div>
              <div class="text-xs text-gray-500">输出 Token</div>
            </div>
            <div class="bg-purple-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-purple-700">{{ usage.summary.total_requests }}</div>
              <div class="text-xs text-gray-500">请求次数</div>
            </div>
          </div>
          <div v-if="usage.by_model.length" class="mb-6">
            <h3 class="font-medium mb-2">按模型统计</h3>
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500 border-b">
                <th class="pb-1">模型</th><th class="pb-1">输入 Token</th><th class="pb-1">输出 Token</th><th class="pb-1">请求数</th>
              </tr></thead>
              <tbody>
                <tr v-for="m in usage.by_model" :key="m.model" class="border-b">
                  <td class="py-1">{{ m.model }}</td>
                  <td>{{ m.prompt_tokens.toLocaleString() }}</td>
                  <td>{{ m.completion_tokens.toLocaleString() }}</td>
                  <td>{{ m.requests }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="usage.by_user.length">
            <h3 class="font-medium mb-2">按用户统计</h3>
            <table class="w-full text-sm">
              <thead><tr class="text-left text-gray-500 border-b">
                <th class="pb-1">用户</th><th class="pb-1">输入 Token</th><th class="pb-1">输出 Token</th><th class="pb-1">请求数</th>
              </tr></thead>
              <tbody>
                <tr v-for="u in usage.by_user" :key="u.username" class="border-b">
                  <td class="py-1">{{ u.username }}</td>
                  <td>{{ u.prompt_tokens.toLocaleString() }}</td>
                  <td>{{ u.completion_tokens.toLocaleString() }}</td>
                  <td>{{ u.requests }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { adminApi, type ModelConfig, type UserRecord, type TokenUsage, type EnvConfig } from '@/api/admin';

// ===== 验证状态 =====
const verified = ref(false);
const keyInput = ref('');
const verifying = ref(false);
const verifyError = ref('');

async function doVerify() {
  if (!keyInput.value.trim()) {
    verifyError.value = '请输入管理员密钥';
    return;
  }
  verifying.value = true;
  verifyError.value = '';
  try {
    await adminApi.verify(keyInput.value.trim());
    localStorage.setItem('admin_key', keyInput.value.trim());
    verified.value = true;
    loadAll();
  } catch {
    verifyError.value = '密钥无效，请重试';
  } finally {
    verifying.value = false;
  }
}

function doLogout() {
  localStorage.removeItem('admin_key');
  verified.value = false;
  keyInput.value = '';
  revealedKeys.value = new Set();
}

onMounted(async () => {
  const saved = localStorage.getItem('admin_key');
  if (saved) {
    keyInput.value = saved;
    try {
      await adminApi.verify(saved);
      verified.value = true;
      loadAll();
    } catch {
      localStorage.removeItem('admin_key');
    }
  }
});

// ===== 标签页 =====
const activeTab = ref('env');
const tabs = [
  { id: 'env', label: '配置' },
  { id: 'models', label: '模型' },
  { id: 'users', label: '用户' },
  { id: 'usage', label: '用量' },
];

function keyLabel(key: string) {
  const map: Record<string, string> = {
    DEEPSEEK_API_KEY: 'DeepSeek API 密钥',
    TAVILY_API_KEY: 'Tavily 搜索 API 密钥',
    OPENROUTER_API_KEY: 'OpenRouter API 密钥',
    SYSTEM_PROMPT_DEFAULT: '默认系统提示词',
    SYSTEM_PROMPT_WITH_CODE_EXEC: '代码执行系统提示词',
  };
  return map[key] || key;
}

function categoryLabel(c: string) {
  const map: Record<string, string> = {
    chat: '对话', image: '图片识别', audio: '音频识别', title: '标题生成',
  };
  return map[c] || c;
}

// ===== 加载全部数据 =====
function loadAll() {
  loadEnv();
  loadModels();
  loadUsers();
  loadUsage();
}

// ===== 配置 =====
const envConfigs = ref<(EnvConfig & { saved?: boolean })[]>([]);
const envLoading = ref(false);
const revealedKeys = ref(new Set<string>());
async function loadEnv() {
  envLoading.value = true;
  try {
    const { data } = await adminApi.getConfigs();
    envConfigs.value = data.map(d => ({ ...d, saved: false }));
  } catch { envConfigs.value = []; }
  finally { envLoading.value = false; }
}
async function saveEnv(item: EnvConfig & { saved?: boolean }) {
  try {
    await adminApi.setConfig(item.key, item.value);
    item.saved = true;
    setTimeout(() => (item.saved = false), 2000);
  } catch { alert('保存失败'); }
}
function toggleReveal(key: string) {
  const s = revealedKeys.value;
  if (s.has(key)) s.delete(key); else s.add(key);
}
async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

// ===== 模型 =====
const models = ref<ModelConfig[]>([]);
const editingModel = ref<(ModelConfig & { _new?: boolean }) | null>(null);
const modelsLoading = ref(false);
async function loadModels() {
  modelsLoading.value = true;
  try { const { data } = await adminApi.getModels(); models.value = data; }
  catch { models.value = []; }
  finally { modelsLoading.value = false; }
}
function startNewModel() {
  editingModel.value = {
    key: '', provider: 'deepseek', model: '', thinking: false,
    accept_image: false, accept_audio: false, is_default: false, category: 'chat', _new: true,
  };
}
function editModel(m: ModelConfig) {
  editingModel.value = { ...m };
}
async function saveModel() {
  if (!editingModel.value) return;
  try {
    await adminApi.upsertModel(editingModel.value.key, editingModel.value as ModelConfig);
    editingModel.value = null;
    await loadModels();
  } catch { alert('保存失败'); }
}
async function removeModel(key: string) {
  if (!confirm(`确定删除模型 "${key}"？`)) return;
  try { await adminApi.deleteModel(key); await loadModels(); }
  catch { alert('删除失败'); }
}

// ===== 用户 =====
const users = ref<UserRecord[]>([]);
const usersLoading = ref(false);
async function loadUsers() {
  usersLoading.value = true;
  try { const { data } = await adminApi.getUsers(); users.value = data; }
  catch { users.value = []; }
  finally { usersLoading.value = false; }
}
async function removeUser(id: number) {
  if (!confirm(`确定删除用户 ${id}？此操作不可撤销。`)) return;
  try { await adminApi.deleteUser(id); await loadUsers(); }
  catch { alert('删除失败'); }
}

// ===== 用量 =====
const usage = ref<TokenUsage | null>(null);
const usageLoading = ref(false);
async function loadUsage() {
  usageLoading.value = true;
  try { const { data } = await adminApi.getTokenUsage(); usage.value = data; }
  catch { usage.value = null; }
  finally { usageLoading.value = false; }
}
</script>
