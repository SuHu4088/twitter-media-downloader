<template>
  <div class="login-container">
    <div class="login-box">
      <h2 class="login-title">Twitter Monitor</h2>
      <p class="login-subtitle">推特监听系统</p>
      <el-form ref="formRef" :model="form" :rules="rules" class="login-form">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  loading.value = true
  try {
    userStore.setToken('mock-token')
    userStore.setUserInfo({
      id: 1,
      username: form.username,
      email: `${form.username}@example.com`
    })
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (error) {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.login-title {
  text-align: center;
  font-size: 28px;
  color: #303133;
  margin-bottom: 10px;
}

.login-subtitle {
  text-align: center;
  color: #909399;
  margin-bottom: 30px;
}

.login-form {
  .login-btn {
    width: 100%;
  }
}
</style>
