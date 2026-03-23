<template>
  <div class="not-found-page">
    <div class="not-found-content">
      <h1>404</h1>
      <p>页面不存在</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<style scoped lang="scss">
.not-found-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f5f7fa;

  .not-found-content {
    text-align: center;

    h1 {
      font-size: 120px;
      color: #409eff;
      margin-bottom: 20px;
    }

    p {
      font-size: 24px;
      color: #606266;
      margin-bottom: 30px;
    }
  }
}
</style>
