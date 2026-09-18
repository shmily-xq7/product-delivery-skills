<template>
  <section>
    <el-tabs :model-value="activeName" @tab-change="changeTab">
      <el-tab-pane v-for="tab in tabs" :key="tab.routeName" :label="tab.label" :name="tab.routeName" />
    </el-tabs>
    <router-view />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type TabItem = { label: string; routeName: string }
defineProps<{ tabs: TabItem[] }>()

const route = useRoute()
const router = useRouter()
const activeName = computed(() => String(route.name || ''))
const changeTab = (name: string | number) => {
  const routeName = String(name)
  if (routeName !== activeName.value) router.push({ name: routeName })
}
</script>
