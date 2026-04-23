<template>
  <aside
    class="bg-white border-r border-gray-200 flex flex-col shadow-sm transition-all duration-300"
    :class="collapsed ? 'w-16' : 'w-64'"
  >
    <!-- 新对话按钮：折叠时只显示图标 -->
    <div class="p-4 border-b border-gray-100">
      <button
        @click="handleNewSession"
        class="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm"
        :title="collapsed ? '新对话' : ''"
      >
        <PlusIcon class="w-5 h-5" />
        <span v-if="!collapsed">新对话</span>
      </button>
    </div>

    <!-- 会话列表：折叠时只显示图标占位 -->
    <div class="flex-1 overflow-y-auto p-2 space-y-1">
      <div
        v-for="session in sessionStore.sessions"
        :key="session.session_id"
        @click="selectSession(session.session_id)"
        class="group relative p-3 rounded-xl cursor-pointer transition-all"
        :class="[
          session.session_id === sessionStore.currentSessionId
            ? 'bg-blue-50 text-blue-700'
            : 'hover:bg-gray-50 text-gray-700',
          collapsed ? 'flex justify-center' : ''
        ]"
      >
        <div v-if="!collapsed" class="flex items-center justify-between">
          <span class="text-sm font-medium">{{ formatDate(session.created_at) }}</span>
          <button
            @click.stop="deleteSessionConfirm(session.session_id)"
            class="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-gray-200 transition"
          >
            <TrashIcon class="w-4 h-4 text-gray-500 hover:text-red-500" />
          </button>
        </div>
        <!-- 折叠时显示一个聊天图标 -->
        <div v-else class="flex flex-col items-center">
          <ChatBubbleLeftIcon class="w-5 h-5" />
          <div class="w-1 h-1 bg-gray-300 rounded-full mt-1"></div>
        </div>
        <p v-if="!collapsed" class="text-xs text-gray-400 truncate mt-1">
          {{ session.session_id.slice(0, 8) }}
        </p>
      </div>
    </div>

    <!-- 用户信息区域：折叠时只显示头像或图标 -->
    <div class="p-4 border-t border-gray-100">
      <div v-if="!collapsed" class="flex items-center justify-between">
        <span class="text-sm font-medium text-gray-700">{{ authStore.user?.username }}</span>
        <button @click="authStore.logout" class="text-sm text-red-500 hover:text-red-600">登出</button>
      </div>
      <div v-else class="flex flex-col items-center space-y-2">
        <UserCircleIcon class="w-6 h-6 text-gray-500" />
        <button @click="authStore.logout" class="text-xs text-red-400 hover:text-red-500">登出</button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { PlusIcon, TrashIcon, ChatBubbleLeftIcon, UserCircleIcon } from '@heroicons/vue/24/outline';
import { useSessionStore } from '@/stores/session';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

defineProps<{
  collapsed: boolean;
}>();

const sessionStore = useSessionStore();
const authStore = useAuthStore();
const router = useRouter();

onMounted(() => {
  sessionStore.fetchSessions();
});

function formatDate(dateStr: string) {
  const match = dateStr.match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/);
  if (!match) return dateStr;
  const [, year, month, day, hour, minute, second] = match.map(Number);
  const utcTimestamp = Date.UTC(year, month - 1, day, hour, minute, second);
  return new Date(utcTimestamp).toLocaleDateString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

async function handleNewSession() {
  const newId = await sessionStore.createSession();
  sessionStore.setCurrentSession(newId);
}

function selectSession(sessionId: string) {
  sessionStore.setCurrentSession(sessionId);
}

async function deleteSessionConfirm(sessionId: string) {
  if (confirm('确定删除此会话？')) {
    await sessionStore.deleteSession(sessionId);
  }
}
</script>