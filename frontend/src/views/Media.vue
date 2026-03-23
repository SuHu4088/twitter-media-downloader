<template>
  <div class="media-page page-container">
    <div class="page-header mb-20">
      <el-form :inline="true" :model="filters">
        <el-form-item label="媒体类型">
          <el-select v-model="filters.media_type" placeholder="全部" clearable>
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
            <el-option label="GIF" value="gif" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号">
          <el-select v-model="filters.account_id" placeholder="全部" clearable>
            <el-option label="账号1" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchMedia">搜索</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="media-grid">
      <div v-for="item in mediaList" :key="item.id" class="media-card">
        <div class="media-preview">
          <img v-if="item.media_type === 'image'" :src="item.media_url" :alt="item.tweet_id" />
          <div v-else class="video-placeholder">
            <el-icon size="48"><VideoPlay /></el-icon>
          </div>
        </div>
        <div class="media-info">
          <div class="media-meta">
            <span>{{ item.account_name }}</span>
            <el-tag size="small">{{ item.media_type }}</el-tag>
          </div>
          <div class="media-size">{{ formatSize(item.file_size) }}</div>
        </div>
      </div>
    </div>

    <el-pagination
      class="mt-20"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[20, 40, 60]"
      layout="total, sizes, prev, pager, next"
      @change="fetchMedia"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

interface Media {
  id: number
  tweet_id: string
  media_type: 'image' | 'video' | 'gif'
  media_url: string
  file_size: number
  account_name: string
}

const mediaList = ref<Media[]>([])
const loading = ref(false)

const filters = reactive({
  media_type: '',
  account_id: null as number | null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

async function fetchMedia() {
  loading.value = true
  try {
    mediaList.value = [
      {
        id: 1,
        tweet_id: '123456',
        media_type: 'image',
        media_url: 'https://via.placeholder.com/300',
        file_size: 1024 * 500,
        account_name: 'user1'
      }
    ]
    pagination.total = 1
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMedia()
})
</script>

<style scoped lang="scss">
.media-page {
  .media-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
  }

  .media-card {
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s;

    &:hover {
      transform: translateY(-4px);
    }

    .media-preview {
      height: 150px;
      background: #f5f7fa;
      display: flex;
      align-items: center;
      justify-content: center;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .video-placeholder {
        color: #909399;
      }
    }

    .media-info {
      padding: 12px;

      .media-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }

      .media-size {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}
</style>
