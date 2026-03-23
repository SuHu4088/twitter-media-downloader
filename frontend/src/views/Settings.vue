<template>
  <div class="settings-page page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本设置" name="basic">
        <el-form :model="basicForm" label-width="120px" class="settings-form">
          <el-form-item label="系统名称">
            <el-input v-model="basicForm.systemName" />
          </el-form-item>
          <el-form-item label="下载路径">
            <el-input v-model="basicForm.downloadPath">
              <template #append>
                <el-button>选择</el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="自动同步">
            <el-switch v-model="basicForm.autoSync" />
          </el-form-item>
          <el-form-item label="同步间隔">
            <el-input-number v-model="basicForm.syncInterval" :min="1" :max="24" />
            <span class="ml-10">小时</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveBasicSettings">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="通知设置" name="notification">
        <el-form :model="notifyForm" label-width="120px" class="settings-form">
          <el-form-item label="启用通知">
            <el-switch v-model="notifyForm.enabled" />
          </el-form-item>
          <el-form-item label="邮件通知">
            <el-input v-model="notifyForm.email" placeholder="输入邮箱地址" />
          </el-form-item>
          <el-form-item label="通知事件">
            <el-checkbox-group v-model="notifyForm.events">
              <el-checkbox label="download_complete">下载完成</el-checkbox>
              <el-checkbox label="sync_complete">同步完成</el-checkbox>
              <el-checkbox label="error">错误提醒</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveNotifySettings">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="存储设置" name="storage">
        <el-form :model="storageForm" label-width="120px" class="settings-form">
          <el-form-item label="最大存储">
            <el-input-number v-model="storageForm.maxSize" :min="1" :max="1000" />
            <span class="ml-10">GB</span>
          </el-form-item>
          <el-form-item label="自动清理">
            <el-switch v-model="storageForm.autoCleanup" />
          </el-form-item>
          <el-form-item label="保留天数">
            <el-input-number v-model="storageForm.keepDays" :min="7" :max="365" />
            <span class="ml-10">天</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveStorageSettings">保存设置</el-button>
            <el-button type="danger" @click="clearStorage">清理存储</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('basic')

const basicForm = reactive({
  systemName: 'Twitter Monitor',
  downloadPath: '/data/downloads',
  autoSync: true,
  syncInterval: 6
})

const notifyForm = reactive({
  enabled: false,
  email: '',
  events: ['error'] as string[]
})

const storageForm = reactive({
  maxSize: 100,
  autoCleanup: false,
  keepDays: 30
})

function saveBasicSettings() {
  ElMessage.success('基本设置已保存')
}

function saveNotifySettings() {
  ElMessage.success('通知设置已保存')
}

function saveStorageSettings() {
  ElMessage.success('存储设置已保存')
}

function clearStorage() {
  ElMessageBox.confirm('确定要清理存储吗？此操作不可恢复。', '警告', {
    type: 'warning'
  }).then(() => {
    ElMessage.success('存储清理完成')
  })
}
</script>

<style scoped lang="scss">
.settings-page {
  .settings-form {
    max-width: 600px;
  }
}
</style>
