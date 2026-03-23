<template>
  <div class="engagement-chart" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

interface EngagementData {
  date: string
  likes: number
  retweets: number
  replies: number
}

interface Props {
  data: EngagementData[]
  metrics: string[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  metrics: () => ['likes', 'retweets'],
  loading: false
})

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const metricConfig: Record<string, { name: string; color: string }> = {
  likes: { name: '点赞数', color: '#f56c6c' },
  retweets: { name: '转发数', color: '#409eff' },
  replies: { name: '评论数', color: '#67c23a' }
}

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance) return
  
  const xAxisData = props.data.map(item => item.date)
  
  const series: echarts.LineSeriesOption[] = props.metrics.map(metric => {
    const config = metricConfig[metric]
    return {
      name: config.name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: props.data.map(item => item[metric as keyof EngagementData] as number),
      lineStyle: {
        width: 2,
        color: config.color
      },
      itemStyle: {
        color: config.color
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: config.color + '40' },
          { offset: 1, color: config.color + '05' }
        ])
      }
    }
  })
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      }
    },
    legend: {
      data: props.metrics.map(m => metricConfig[m].name),
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLabel: {
        rotate: 45,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: true
      },
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series
  }
  
  chartInstance.setOption(option, true)
}

function handleResize() {
  chartInstance?.resize()
}

watch(() => props.data, () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

watch(() => props.metrics, () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.engagement-chart {
  width: 100%;
  height: 350px;
}
</style>
