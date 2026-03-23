<template>
  <div class="media-player" ref="playerContainer">
    <div v-if="mediaType === 'video'" class="video-wrapper">
      <video
        ref="videoRef"
        :src="src"
        :poster="poster"
        @loadedmetadata="handleLoadedMetadata"
        @timeupdate="handleTimeUpdate"
        @ended="handleEnded"
        @error="handleError"
        class="video-element"
      />
      
      <div class="video-controls" v-show="showControls">
        <div class="progress-bar" @click="handleProgressClick">
          <div class="progress-buffered" :style="{ width: bufferedPercent + '%' }"></div>
          <div class="progress-played" :style="{ width: progressPercent + '%' }"></div>
          <div class="progress-thumb" :style="{ left: progressPercent + '%' }"></div>
        </div>
        
        <div class="controls-bar">
          <div class="left-controls">
            <el-button :icon="isPlaying ? 'VideoPause' : 'VideoPlay'" circle @click="togglePlay" />
            <div class="time-display">
              <span>{{ formatTime(currentTime) }}</span>
              <span>/</span>
              <span>{{ formatTime(duration) }}</span>
            </div>
          </div>
          
          <div class="right-controls">
            <el-dropdown trigger="click" @command="handleSpeedChange">
              <el-button>
                {{ playbackRate }}x
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="rate in playbackRates" :key="rate" :command="rate">
                    {{ rate }}x
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            
            <div class="volume-control">
              <el-button :icon="isMuted ? 'Mute' : 'Microphone'" circle @click="toggleMute" />
              <el-slider
                v-model="volume"
                :min="0"
                :max="100"
                :show-tooltip="false"
                class="volume-slider"
                @input="handleVolumeChange"
              />
            </div>
            
            <el-button :icon="isFullscreen ? 'Close' : 'FullScreen'" circle @click="toggleFullscreen" />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="mediaType === 'gif'" class="gif-wrapper">
      <img
        ref="gifRef"
        :src="src"
        :alt="alt"
        @click="toggleGifPlay"
        class="gif-element"
        :class="{ paused: !gifPlaying }"
      />
      <div v-if="!gifPlaying" class="gif-overlay" @click="toggleGifPlay">
        <el-icon :size="48"><VideoPlay /></el-icon>
        <span>点击播放</span>
      </div>
    </div>

    <div v-else class="unsupported">
      <el-empty description="不支持的媒体类型" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

interface Props {
  src: string
  mediaType: 'video' | 'gif'
  poster?: string
  alt?: string
  autoplay?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoplay: false
})

const emit = defineEmits<{
  (e: 'error', error: Error): void
  (e: 'ended'): void
  (e: 'play'): void
  (e: 'pause'): void
}>()

const playerContainer = ref<HTMLElement>()
const videoRef = ref<HTMLVideoElement>()
const gifRef = ref<HTMLImageElement>()

const isPlaying = ref(false)
const isMuted = ref(false)
const isFullscreen = ref(false)
const showControls = ref(true)
const currentTime = ref(0)
const duration = ref(0)
const bufferedPercent = ref(0)
const volume = ref(80)
const playbackRate = ref(1)
const gifPlaying = ref(true)

const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]

const progressPercent = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function handleLoadedMetadata() {
  if (videoRef.value) {
    duration.value = videoRef.value.duration
    if (props.autoplay) {
      videoRef.value.play()
      isPlaying.value = true
    }
  }
}

function handleTimeUpdate() {
  if (videoRef.value) {
    currentTime.value = videoRef.value.currentTime
    if (videoRef.value.buffered.length > 0) {
      bufferedPercent.value = (videoRef.value.buffered.end(0) / duration.value) * 100
    }
  }
}

function handleEnded() {
  isPlaying.value = false
  emit('ended')
}

function handleError(e: Event) {
  const error = new Error('视频加载失败')
  emit('error', error)
  ElMessage.error('视频加载失败')
}

function togglePlay() {
  if (!videoRef.value) return
  
  if (isPlaying.value) {
    videoRef.value.pause()
    emit('pause')
  } else {
    videoRef.value.play()
    emit('play')
  }
  isPlaying.value = !isPlaying.value
}

function handleProgressClick(e: MouseEvent) {
  if (!videoRef.value || !playerContainer.value) return
  
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  videoRef.value.currentTime = percent * duration.value
}

function handleSpeedChange(rate: number) {
  if (!videoRef.value) return
  videoRef.value.playbackRate = rate
  playbackRate.value = rate
}

function toggleMute() {
  if (!videoRef.value) return
  videoRef.value.muted = !videoRef.value.muted
  isMuted.value = videoRef.value.muted
}

function handleVolumeChange(val: number) {
  if (!videoRef.value) return
  videoRef.value.volume = val / 100
  if (val === 0) {
    isMuted.value = true
    videoRef.value.muted = true
  } else if (isMuted.value) {
    isMuted.value = false
    videoRef.value.muted = false
  }
}

function toggleFullscreen() {
  if (!playerContainer.value) return
  
  if (document.fullscreenElement) {
    document.exitFullscreen()
    isFullscreen.value = false
  } else {
    playerContainer.value.requestFullscreen()
    isFullscreen.value = true
  }
}

function toggleGifPlay() {
  gifPlaying.value = !gifPlaying.value
}

let controlsTimeout: ReturnType<typeof setTimeout> | null = null

function showControlsTemporarily() {
  showControls.value = true
  if (controlsTimeout) {
    clearTimeout(controlsTimeout)
  }
  controlsTimeout = setTimeout(() => {
    if (isPlaying.value) {
      showControls.value = false
    }
  }, 3000)
}

function handleMouseMove() {
  showControlsTemporarily()
}

function handleKeyDown(e: KeyboardEvent) {
  if (!videoRef.value) return
  
  switch (e.key) {
    case ' ':
      e.preventDefault()
      togglePlay()
      break
    case 'ArrowLeft':
      videoRef.value.currentTime -= 5
      break
    case 'ArrowRight':
      videoRef.value.currentTime += 5
      break
    case 'ArrowUp':
      volume.value = Math.min(100, volume.value + 10)
      handleVolumeChange(volume.value)
      break
    case 'ArrowDown':
      volume.value = Math.max(0, volume.value - 10)
      handleVolumeChange(volume.value)
      break
    case 'f':
      toggleFullscreen()
      break
    case 'm':
      toggleMute()
      break
  }
}

onMounted(() => {
  if (playerContainer.value) {
    playerContainer.value.addEventListener('mousemove', handleMouseMove)
    playerContainer.value.addEventListener('keydown', handleKeyDown)
  }
})

onUnmounted(() => {
  if (playerContainer.value) {
    playerContainer.value.removeEventListener('mousemove', handleMouseMove)
    playerContainer.value.removeEventListener('keydown', handleKeyDown)
  }
  if (controlsTimeout) {
    clearTimeout(controlsTimeout)
  }
})

watch(() => props.src, () => {
  currentTime.value = 0
  duration.value = 0
  isPlaying.value = false
})
</script>

<style scoped lang="scss">
.media-player {
  width: 100%;
  height: 100%;
  background: #000;
  position: relative;

  .video-wrapper {
    width: 100%;
    height: 100%;
    position: relative;

    .video-element {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .video-controls {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
      padding: 20px 16px 16px;
      transition: opacity 0.3s;

      .progress-bar {
        height: 4px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 2px;
        cursor: pointer;
        position: relative;
        margin-bottom: 12px;

        &:hover {
          height: 6px;

          .progress-thumb {
            transform: translateX(-50%) scale(1.5);
          }
        }

        .progress-buffered,
        .progress-played {
          position: absolute;
          top: 0;
          left: 0;
          height: 100%;
          border-radius: 2px;
        }

        .progress-buffered {
          background: rgba(255, 255, 255, 0.5);
        }

        .progress-played {
          background: var(--el-color-primary);
        }

        .progress-thumb {
          position: absolute;
          top: 50%;
          transform: translateX(-50%) translateY(-50%);
          width: 12px;
          height: 12px;
          background: var(--el-color-primary);
          border-radius: 50%;
          transition: transform 0.2s;
        }
      }

      .controls-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .left-controls,
        .right-controls {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .time-display {
          color: #fff;
          font-size: 14px;
          font-family: monospace;
        }

        .volume-control {
          display: flex;
          align-items: center;
          gap: 8px;

          .volume-slider {
            width: 80px;
          }
        }
      }
    }
  }

  .gif-wrapper {
    width: 100%;
    height: 100%;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;

    .gif-element {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;

      &.paused {
        opacity: 0.5;
      }
    }

    .gif-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      color: #fff;
      cursor: pointer;
      background: rgba(0, 0, 0, 0.3);
    }
  }
}
</style>
