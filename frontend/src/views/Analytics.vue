<template>
  <div class="analytics-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>媒体类型分布</template>
          <div class="chart-container" ref="pieChartRef"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>账号活跃度</template>
          <div class="chart-container" ref="barChartRef"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>下载趋势分析</template>
          <div class="chart-container-large" ref="lineChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const pieChartRef = ref<HTMLElement>()
const barChartRef = ref<HTMLElement>()
const lineChartRef = ref<HTMLElement>()

onMounted(() => {
  if (pieChartRef.value) {
    const chart = echarts.init(pieChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          data: [
            { value: 1048, name: '图片' },
            { value: 735, name: '视频' },
            { value: 580, name: 'GIF' }
          ]
        }
      ]
    })
  }

  if (barChartRef.value) {
    const chart = echarts.init(barChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: ['账号1', '账号2', '账号3', '账号4', '账号5']
      },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: [200, 150, 100, 80, 50] }]
    })
  }

  if (lineChartRef.value) {
    const chart = echarts.init(lineChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['图片', '视频', 'GIF'] },
      xAxis: {
        type: 'category',
        data: ['1月', '2月', '3月', '4月', '5月', '6月']
      },
      yAxis: { type: 'value' },
      series: [
        { name: '图片', type: 'line', data: [120, 132, 101, 134, 90, 230] },
        { name: '视频', type: 'line', data: [220, 182, 191, 234, 290, 330] },
        { name: 'GIF', type: 'line', data: [150, 232, 201, 154, 190, 330] }
      ]
    })
  }
})
</script>

<style scoped lang="scss">
.analytics-page {
  .chart-container {
    height: 300px;
  }

  .chart-container-large {
    height: 400px;
  }
}
</style>
