<template>
  <div class="flex h-screen bg-gray-50">
    <!-- 侧边栏：动态宽度 -->
    <SessionSidebar :collapsed="isCollapsed" />
    
    <!-- 主内容区：自动占据剩余宽度 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部栏可放置折叠按钮（可选） -->
      <div class="bg-white border-b border-gray-200 px-4 py-2 flex items-center">
        <button
          @click="toggleSidebar"
          class="p-2 rounded-md hover:bg-gray-100 transition"
          :title="isCollapsed ? '展开侧边栏' : '折叠侧边栏'"
        >
          <ChevronLeftIcon v-if="!isCollapsed" class="w-5 h-5 text-gray-600" />
          <ChevronRightIcon v-else class="w-5 h-5 text-gray-600" />
        </button>
        <h1 class="ml-2 text-lg font-semibold text-gray-800">Better Deepseek</h1>
      </div>
      
      <!-- 路由内容 -->
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import SessionSidebar from '@/components/chat/SessionSidebar.vue';

// 折叠状态（持久化到 localStorage）
const isCollapsed = ref(false);

onMounted(() => {
  const saved = localStorage.getItem('sidebar-collapsed');
  if (saved !== null) isCollapsed.value = saved === 'true';
});

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value;
  localStorage.setItem('sidebar-collapsed', String(isCollapsed.value));
}
</script>