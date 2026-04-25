<template>
  <div class="flex h-screen bg-gray-50">
    <!-- PC 侧边栏：md 以上正常显示；移动端隐藏 -->
    <SessionSidebar
      :collapsed="isCollapsed"
      class="hidden md:flex"
    />

    <div
      v-if="mobileDrawerOpen"
      class="fixed inset-0 z-40 bg-black/50 md:hidden"
      @click="mobileDrawerOpen = false"
    />

    <SessionSidebar
      :collapsed="false"
      class="fixed inset-y-0 left-0 z-50 w-64 md:hidden transition-transform duration-300"
      :class="mobileDrawerOpen ? 'translate-x-0' : '-translate-x-full'"
    />

    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部栏 -->
      <div class="bg-white border-b border-gray-200 px-3 md:px-4 py-2 flex items-center gap-2">
        <button
          @click="toggleSidebar"
          class="p-2 rounded-md hover:bg-gray-100 transition hidden md:block"
          :title="isCollapsed ? '展开侧边栏' : '折叠侧边栏'"
        >
          <ChevronLeftIcon v-if="!isCollapsed" class="w-5 h-5 text-gray-600" />
          <ChevronRightIcon v-else class="w-5 h-5 text-gray-600" />
        </button>

        <!-- 移动端汉堡按钮 -->
        <button
          @click="mobileDrawerOpen = !mobileDrawerOpen"
          class="p-2 rounded-md hover:bg-gray-100 transition md:hidden"
        >
          <Bars3Icon class="w-6 h-6 text-gray-600" />
        </button>

        <h1 class="text-base md:text-lg font-semibold text-gray-800 mr-auto">Better Deepseek</h1>
      </div>

      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ChevronLeftIcon, ChevronRightIcon, Bars3Icon } from '@heroicons/vue/24/outline';
import SessionSidebar from '@/components/chat/SessionSidebar.vue';

const isCollapsed = ref(false);
const mobileDrawerOpen = ref(false);

onMounted(() => {
  const saved = localStorage.getItem('sidebar-collapsed');
  if (saved !== null) isCollapsed.value = saved === 'true';
});

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value;
  localStorage.setItem('sidebar-collapsed', String(isCollapsed.value));
}
</script>