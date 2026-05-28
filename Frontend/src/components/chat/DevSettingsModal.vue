<template>
  <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="close">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
      <h3 class="text-lg font-semibold mb-4">开发者设置</h3>

      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1">默认系统提示词</label>
          <textarea
            v-model="formData.system_prompt_default"
            class="w-full border rounded px-3 py-2 text-sm font-mono resize-y"
            rows="4"
            placeholder="留空则使用系统默认"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1">代码执行系统提示词</label>
          <textarea
            v-model="formData.system_prompt_with_code_exec"
            class="w-full border rounded px-3 py-2 text-sm font-mono resize-y"
            rows="6"
            placeholder="留空则使用系统默认"
          />
        </div>
        <div class="flex items-center justify-between">
          <label class="text-sm font-medium text-gray-600">沙盒联网</label>
          <label class="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              class="sr-only peer"
              :checked="!formData.sandbox_network_disabled"
              @change="formData.sandbox_network_disabled = !formData.sandbox_network_disabled"
            />
            <div class="w-10 h-5 bg-gray-300 rounded-full peer-checked:bg-blue-600 transition-colors"></div>
            <span class="ml-2 text-sm text-gray-500">{{ formData.sandbox_network_disabled ? '禁用' : '启用' }}</span>
          </label>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1">沙盒存活时间（秒）</label>
          <input
            v-model.number="formData.sandbox_idle_timeout"
            type="number"
            min="60"
            step="60"
            class="w-full border rounded px-3 py-2 text-sm"
          />
          <p class="text-xs text-gray-400 mt-1">
            空闲超过此时间后容器将被自动销毁（默认 3600 秒 = 1 小时）
          </p>
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-6">
        <button @click="close" class="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">取消</button>
        <button
          @click="save"
          :disabled="saving"
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
      <p v-if="saved" class="text-green-600 text-sm mt-2 text-right">已保存</p>
      <p v-if="error" class="text-red-500 text-sm mt-2 text-right">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import { devApi } from '@/api/dev';

const emit = defineEmits<{
  close: [];
}>();

const saving = ref(false);
const saved = ref(false);
const error = ref('');

const formData = reactive({
  system_prompt_default: null as string | null,
  system_prompt_with_code_exec: null as string | null,
  sandbox_network_disabled: true,
  sandbox_idle_timeout: 3600,
});

onMounted(async () => {
  try {
    const { data } = await devApi.getSettings();
    formData.system_prompt_default = data.system_prompt_default || null;
    formData.system_prompt_with_code_exec = data.system_prompt_with_code_exec || null;
    formData.sandbox_network_disabled = data.sandbox_network_disabled;
    formData.sandbox_idle_timeout = data.sandbox_idle_timeout;
  } catch {
    error.value = '加载设置失败';
  }
});

async function save() {
  saving.value = true;
  saved.value = false;
  error.value = '';
  try {
    const payload: Record<string, unknown> = {};
    if (formData.system_prompt_default !== null) {
      payload.system_prompt_default = formData.system_prompt_default || '';
    }
    if (formData.system_prompt_with_code_exec !== null) {
      payload.system_prompt_with_code_exec = formData.system_prompt_with_code_exec || '';
    }
    payload.sandbox_network_disabled = formData.sandbox_network_disabled;
    payload.sandbox_idle_timeout = formData.sandbox_idle_timeout;
    await devApi.updateSettings(payload);
    saved.value = true;
    setTimeout(() => (saved.value = false), 2000);
  } catch {
    error.value = '保存失败';
  } finally {
    saving.value = false;
  }
}

function close() {
  emit('close');
}
</script>
