<template>
  <div class="account-bind">
    <el-card v-if="!isBinding && !bindResult" class="bind-card">
      <template #header>
        <div class="card-header">
          <span>绑定推特账号</span>
        </div>
      </template>
      <div class="bind-content">
        <el-alert
          title="授权说明"
          type="info"
          :closable="false"
          class="mb-20"
        >
          <p>通过OAuth授权绑定您的推特账号，系统将自动获取账号信息并开始监控。</p>
          <p>请确保您已登录需要绑定的推特账号。</p>
        </el-alert>
        <el-button type="primary" size="large" @click="startOAuth" :loading="loading">
          <el-icon><Link /></el-icon>
          开始OAuth授权
        </el-button>
      </div>
    </el-card>

    <el-card v-if="isBinding" class="bind-card">
      <div class="binding-status">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p class="mt-20">正在等待授权...</p>
        <p class="text-secondary">请在弹出的推特授权页面完成授权操作</p>
        <el-button class="mt-20" @click="cancelBinding">取消授权</el-button>
      </div>
    </el-card>

    <el-card v-if="bindResult" class="bind-card">
      <div class="bind-result">
        <el-result
          :icon="bindResult.success ? 'success' : 'error'"
          :title="bindResult.success ? '绑定成功' : '绑定失败'"
          :sub-title="bindResult.message"
        >
          <template #extra>
            <el-button type="primary" @click="resetBind">
              {{ bindResult.success ? '查看账号' : '重新绑定' }}
            </el-button>
          </template>
        </el-result>
        <div v-if="bindResult.success && bindResult.account" class="account-info mt-20">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户名">@{{ bindResult.account.username }}</el-descriptions-item>
            <el-descriptions-item label="显示名称">{{ bindResult.account.display_name }}</el-descriptions-item>
            <el-descriptions-item label="粉丝数">{{ bindResult.account.followers_count }}</el-descriptions-item>
            <el-descriptions-item label="推文数">{{ bindResult.account.tweets_count }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="showOAuthDialog" title="推特授权" width="600px" :close-on-click-modal="false">
      <div class="oauth-dialog">
        <p class="mb-20">请在新窗口中完成推特授权，授权完成后将自动返回。</p>
        <el-input v-model="oauthVerifier" placeholder="请输入授权码（如有）" class="mb-20" />
        <el-button type="primary" @click="completeOAuth" :loading="verifying">
          完成授权
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { twitterApi, OAuthUrlResponse, TwitterAccount } from '@/api/twitter'

interface BindResult {
  success: boolean
  message: string
  account?: TwitterAccount
}

const router = useRouter()
const loading = ref(false)
const isBinding = ref(false)
const bindResult = ref<BindResult | null>(null)
const showOAuthDialog = ref(false)
const oauthVerifier = ref('')
const verifying = ref(false)
const oauthData = ref<OAuthUrlResponse | null>(null)
const oauthWindow = ref<Window | null>(null)

async function startOAuth() {
  loading.value = true
  try {
    const data = await twitterApi.getOAuthUrl()
    oauthData.value = data
    isBinding.value = true
    const width = 600
    const height = 700
    const left = (window.screen.width - width) / 2
    const top = (window.screen.height - height) / 2
    oauthWindow.value = window.open(
      data.oauth_url,
      'TwitterOAuth',
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,resizable=yes`
    )
    showOAuthDialog.value = true
    checkOAuthWindow()
  } catch (error) {
    ElMessage.error('获取授权链接失败')
    isBinding.value = false
  } finally {
    loading.value = false
  }
}

function checkOAuthWindow() {
  const checkInterval = setInterval(() => {
    if (oauthWindow.value?.closed) {
      clearInterval(checkInterval)
      if (isBinding.value && !bindResult.value) {
        showOAuthDialog.value = false
      }
    }
  }, 500)
}

async function completeOAuth() {
  if (!oauthData.value) return
  
  verifying.value = true
  try {
    const urlParams = new URLSearchParams(window.location.search)
    const oauthToken = urlParams.get('oauth_token') || oauthData.value.oauth_token
    const verifier = oauthVerifier.value || urlParams.get('oauth_verifier')
    
    if (!verifier) {
      ElMessage.warning('请输入授权码')
      return
    }

    const account = await twitterApi.oauthCallback({
      oauth_token: oauthToken,
      oauth_verifier: verifier
    })
    
    bindResult.value = {
      success: true,
      message: '账号绑定成功，系统将开始监控该账号',
      account
    }
    showOAuthDialog.value = false
    isBinding.value = false
    oauthWindow.value?.close()
  } catch (error: any) {
    bindResult.value = {
      success: false,
      message: error.message || '授权失败，请重试'
    }
    showOAuthDialog.value = false
    isBinding.value = false
  } finally {
    verifying.value = false
  }
}

function cancelBinding() {
  isBinding.value = false
  oauthWindow.value?.close()
  oauthData.value = null
}

function resetBind() {
  if (bindResult.value?.success) {
    router.push('/accounts')
  } else {
    bindResult.value = null
    isBinding.value = false
    oauthData.value = null
    oauthVerifier.value = ''
  }
}
</script>

<style scoped lang="scss">
.account-bind {
  .bind-card {
    max-width: 600px;
    margin: 0 auto;
  }

  .bind-content {
    text-align: center;
    padding: 20px 0;
  }

  .binding-status {
    text-align: center;
    padding: 40px 0;

    .is-loading {
      color: var(--el-color-primary);
    }
  }

  .oauth-dialog {
    text-align: center;
  }

  .text-secondary {
    color: var(--el-text-color-secondary);
  }
}
</style>
