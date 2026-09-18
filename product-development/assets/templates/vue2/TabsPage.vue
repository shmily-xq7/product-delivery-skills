<template>
  <section>
    <el-tabs :value="activeName" @tab-click="changeTab">
      <el-tab-pane v-for="tab in tabs" :key="tab.routeName" :label="tab.label" :name="tab.routeName" />
    </el-tabs>
    <router-view />
  </section>
</template>

<script>
export default {
  name: 'TabsPage',
  props: {
    tabs: { type: Array, required: true }
  },
  computed: {
    activeName() { return String(this.$route.name || '') }
  },
  methods: {
    changeTab(tab) {
      if (tab.name !== this.activeName) this.$router.push({ name: tab.name })
    }
  }
}
</script>
