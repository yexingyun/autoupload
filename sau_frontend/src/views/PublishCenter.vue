<template>
  <div class="publish-center">
    <!-- Tab管理区域 -->
    <div class="tab-management">
      <div class="tab-header">
        <div class="tab-list">
          <div 
            v-for="tab in tabs" 
            :key="tab.name"
            :class="['tab-item', { active: activeTab === tab.name }]"
            @click="activeTab = tab.name"
          >
            <span>{{ tab.label }}</span>
            <el-icon 
              v-if="tabs.length > 1"
              class="close-icon" 
              @click.stop="removeTab(tab.name)"
            >
              <Close />
            </el-icon>
          </div>
        </div>
        <div class="tab-actions">
          <el-button 
            type="primary" 
            size="small" 
            @click="addTab"
            class="add-tab-btn"
          >
            <el-icon><Plus /></el-icon>
            添加Tab
          </el-button>
          <el-button 
            type="success" 
            size="small" 
            @click="batchPublish"
            :loading="batchPublishing"
            class="batch-publish-btn"
          >
            批量发布
          </el-button>
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="publish-content">
      <div class="tab-content-wrapper">
        <div 
          v-for="tab in tabs" 
          :key="tab.name"
          v-show="activeTab === tab.name"
          class="tab-content"
        >
          <!-- 发布状态提示 -->
          <div v-if="tab.publishStatus" class="publish-status">
            <el-alert
              :title="tab.publishStatus.message"
              :type="tab.publishStatus.type"
              :closable="false"
              show-icon
            />
          </div>

          <!-- 上传区域（视频/图片） -->
          <div class="upload-section">
            <h3>{{ tab.publishType === 'note' ? '图片' : '视频' }}</h3>
            <div class="upload-options">
              <el-button type="primary" @click="showUploadOptions(tab)" class="upload-btn">
                <el-icon><Upload /></el-icon>
                上传{{ tab.publishType === 'note' ? '图片' : '视频' }}
              </el-button>
            </div>

            <!-- 已上传文件列表 -->
            <div v-if="tab.fileList.length > 0" class="uploaded-files">
              <h4>已上传文件：</h4>
              <div class="file-list">
                <div v-for="(file, index) in tab.fileList" :key="index" class="file-item">
                  <!-- 图文模式显示图片缩略图 -->
                  <template v-if="tab.publishType === 'note'">
                    <div class="image-thumbnail-wrapper">
                      <img :src="file.url" class="image-thumbnail" @click="previewImage(file.url)" />
                    </div>
                    <span class="file-name-text">{{ file.name }}</span>
                  </template>
                  <!-- 视频模式显示链接 -->
                  <template v-else>
                    <el-link :href="file.url" target="_blank" type="primary">{{ file.name }}</el-link>
                  </template>
                  <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(2) }}MB</span>
                  <el-button type="danger" size="small" @click="removeFile(tab, index)">删除</el-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 上传选项弹窗 -->
          <el-dialog
            v-model="uploadOptionsVisible"
            title="选择上传方式"
            width="400px"
            class="upload-options-dialog"
          >
            <div class="upload-options-content">
              <el-button type="primary" @click="selectLocalUpload" class="option-btn">
                <el-icon><Upload /></el-icon>
                本地上传
              </el-button>
              <el-button type="success" @click="selectMaterialLibrary" class="option-btn">
                <el-icon><Folder /></el-icon>
                素材库
              </el-button>
            </div>
          </el-dialog>

          <!-- 本地上传弹窗 -->
          <el-dialog
            v-model="localUploadVisible"
            :title="currentUploadTab?.publishType === 'note' ? '本地上传图片' : '本地上传视频'"
            width="600px"
            class="local-upload-dialog"
          >
            <el-upload
              class="video-upload"
              drag
              :auto-upload="true"
              :action="`${apiBaseUrl}/upload`"
              :on-success="(response, file) => handleUploadSuccess(response, file, currentUploadTab)"
              :on-error="handleUploadError"
              multiple
              :accept="currentUploadTab?.publishType === 'note' ? 'image/*' : 'video/*'"
              :headers="authHeaders"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                将{{ currentUploadTab?.publishType === 'note' ? '图片' : '视频' }}文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  <template v-if="currentUploadTab?.publishType === 'note'">
                    支持JPG、PNG、WebP等图片格式，可上传多张图片
                  </template>
                  <template v-else>
                    支持MP4、AVI等视频格式，可上传多个文件
                  </template>
                </div>
              </template>
            </el-upload>
          </el-dialog>

          <!-- 批量发布进度对话框 -->
          <el-dialog
            v-model="batchPublishDialogVisible"
            title="批量发布进度"
            width="500px"
            :close-on-click-modal="false"
            :close-on-press-escape="false"
            :show-close="false"
          >
            <div class="publish-progress">
              <el-progress 
                :percentage="publishProgress"
                :status="publishProgress === 100 ? 'success' : ''"
              />
              <div v-if="currentPublishingTab" class="current-publishing">
                正在发布：{{ currentPublishingTab.label }}
              </div>
              
              <!-- 发布结果列表 -->
              <div class="publish-results" v-if="publishResults.length > 0">
                <div 
                  v-for="(result, index) in publishResults" 
                  :key="index"
                  :class="['result-item', result.status]"
                >
                  <el-icon v-if="result.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
                  <el-icon v-else><InfoFilled /></el-icon>
                  <span class="label">{{ result.label }}</span>
                  <span class="message">{{ result.message }}</span>
                </div>
              </div>
            </div>
            
            <template #footer>
              <div class="dialog-footer">
                <el-button 
                  @click="cancelBatchPublish" 
                  :disabled="publishProgress === 100"
                >
                  取消发布
                </el-button>
                <el-button 
                  type="primary" 
                  @click="batchPublishDialogVisible = false"
                  v-if="publishProgress === 100"
                >
                  关闭
                </el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 素材库选择弹窗 -->
          <el-dialog
            v-model="materialLibraryVisible"
            title="选择素材"
            width="800px"
            class="material-library-dialog"
          >
            <div class="material-library-content">
              <el-checkbox-group v-model="selectedMaterials">
                <div class="material-list">
                  <div
                    v-for="material in materials"
                    :key="material.id"
                    class="material-item"
                  >
                    <el-checkbox :label="material.id" class="material-checkbox">
                      <div class="material-info">
                        <div class="material-name">{{ material.filename }}</div>
                        <div class="material-details">
                          <span class="file-size">{{ material.filesize }}MB</span>
                          <span class="upload-time">{{ material.upload_time }}</span>
                        </div>
                      </div>
                    </el-checkbox>
                  </div>
                </div>
              </el-checkbox-group>
            </div>
            <template #footer>
              <div class="dialog-footer">
                <el-button @click="materialLibraryVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmMaterialSelection">确定</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 图片预览弹窗 -->
          <el-dialog
            v-model="imagePreviewVisible"
            title="图片预览"
            width="600px"
            class="image-preview-dialog"
          >
            <div class="image-preview-container">
              <img :src="previewImageUrl" style="max-width: 100%; max-height: 70vh;" />
            </div>
          </el-dialog>

          <!-- 账号选择 -->
          <div class="account-section">
            <h3>账号</h3>
            <div class="account-display">
              <div class="selected-accounts">
                <el-tag
                  v-for="(account, index) in tab.selectedAccounts"
                  :key="index"
                  closable
                  @close="removeAccount(tab, index)"
                  class="account-tag"
                >
                  {{ getAccountDisplayName(account) }}
                </el-tag>
              </div>
              <div class="account-list">
                <div
                  v-for="account in accountStore.accounts"
                  :key="account.id"
                  :class="['account-card', { 'is-selected': tab.selectedAccounts.includes(account.id) }]"
                  @click="toggleAccount(tab, account.id)"
                >
                  <div class="account-card-content">
                    <span class="account-name">{{ account.name }}</span>
                    <el-tag
                      :type="getPlatformTagType(account.platform)"
                      effect="plain"
                      size="small"
                      class="platform-mini-tag"
                    >
                      {{ account.platform }}
                    </el-tag>
                  </div>
                  <el-icon v-if="tab.selectedAccounts.includes(account.id)" class="check-icon">
                    <Check />
                  </el-icon>
                </div>
              </div>
            </div>
          </div>

          <!-- 平台选择（由账号自动推导，也可手动调整） -->
          <div class="platform-section">
            <h3>平台</h3>
            <el-radio-group v-model="tab.selectedPlatform" class="platform-radios">
              <el-radio
                v-for="platform in platforms"
                :key="platform.key"
                :label="platform.key"
                class="platform-radio"
                :disabled="tab.selectedAccounts.length > 0"
              >
                {{ platform.name }}
                <span v-if="getPlatformAccountCount(tab, platform.key) > 0" class="platform-count">
                  ({{ getPlatformAccountCount(tab, platform.key) }}个账号)
                </span>
              </el-radio>
            </el-radio-group>
            <div v-if="tab.selectedAccounts.length > 0" class="platform-hint">
              <el-icon><InfoFilled /></el-icon>
              已根据所选账号自动匹配平台，清除所有已选账号后可手动切换
            </div>
          </div>

          <!-- 发布类型切换 -->
          <div class="publish-type-section">
            <h3>发布类型</h3>
            <el-radio-group v-model="tab.publishType" class="publish-type-radios">
              <el-radio-button label="video">
                <el-icon><VideoCamera /></el-icon> 视频发布
              </el-radio-button>
              <el-radio-button label="note">
                <el-icon><Picture /></el-icon> 图文发布
              </el-radio-button>
            </el-radio-group>
          </div>

          <!-- 原创声明 -->
          <div class="original-section">
            <el-checkbox
              v-model="tab.isOriginal"
              label="声明原创"
              class="original-checkbox"
            />
          </div>

          <!-- 草稿选项 (仅在视频号可见) -->
          <div v-if="tab.selectedPlatform === 2" class="draft-section">
            <el-checkbox
              v-model="tab.isDraft"
              label="视频号仅保存草稿(用手机发布)"
              class="draft-checkbox"
            />
          </div>

          <!-- 正文描述 -->
          <div class="desc-section">
            <h3>正文描述</h3>
            <el-input
              v-model="tab.desc"
              type="textarea"
              :rows="5"
              :placeholder="tab.publishType === 'note' ? '请输入图文正文内容' : '请输入视频简介（可选）'"
              maxlength="1000"
              show-word-limit
              class="desc-input"
            />
          </div>

          <!-- 标签 (仅在抖音可见) -->
          <div v-if="tab.selectedPlatform === 3" class="product-section">
            <h3>商品链接</h3>
            <el-input
              v-model="tab.productTitle"
              type="text"
              :rows="1"
              placeholder="请输入商品名称"
              maxlength="200"
              class="product-name-input"
            />
            <el-input
              v-model="tab.productLink"
              type="text"
              :rows="1"
              placeholder="请输入商品链接"
              maxlength="200"
              class="product-link-input"
            />
          </div>

          <!-- 标题输入 -->
          <div class="title-section">
            <h3>标题</h3>
            <el-input
              v-model="tab.title"
              type="textarea"
              :rows="3"
              placeholder="请输入标题"
              maxlength="100"
              show-word-limit
              class="title-input"
            />
          </div>

          <!-- 话题输入 -->
          <div class="topic-section">
            <h3>话题</h3>
            <div class="topic-display">
              <div class="selected-topics">
                <el-tag
                  v-for="(topic, index) in tab.selectedTopics"
                  :key="index"
                  closable
                  @close="removeTopic(tab, index)"
                  class="topic-tag"
                >
                  #{{ topic }}
                </el-tag>
              </div>
              <el-button 
                type="primary" 
                plain 
                @click="openTopicDialog(tab)"
                class="select-topic-btn"
              >
                添加话题
              </el-button>
            </div>
          </div>

          <!-- 添加话题弹窗 -->
          <el-dialog
            v-model="topicDialogVisible"
            title="添加话题"
            width="600px"
            class="topic-dialog"
          >
            <div class="topic-dialog-content">
              <!-- 自定义话题输入 -->
              <div class="custom-topic-input">
                <el-input
                  v-model="customTopic"
                  placeholder="输入自定义话题"
                  class="custom-input"
                >
                  <template #prepend>#</template>
                </el-input>
                <el-button type="primary" @click="addCustomTopic">添加</el-button>
              </div>

              <!-- 推荐话题 -->
              <div class="recommended-topics">
                <h4>推荐话题</h4>
                <div class="topic-grid">
                  <el-button
                    v-for="topic in recommendedTopics"
                    :key="topic"
                    :type="currentTab?.selectedTopics?.includes(topic) ? 'primary' : 'default'"
                    @click="toggleRecommendedTopic(topic)"
                    class="topic-btn"
                  >
                    {{ topic }}
                  </el-button>
                </div>
              </div>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="topicDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmTopicSelection">确定</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 定时发布 -->
          <div class="schedule-section">
            <h3>定时发布</h3>
            <div class="schedule-controls">
              <el-switch
                v-model="tab.scheduleEnabled"
                active-text="定时发布"
                inactive-text="立即发布"
              />
              <div v-if="tab.scheduleEnabled" class="schedule-settings">
                <div class="schedule-item">
                  <span class="label">每天发布视频数：</span>
                  <el-select v-model="tab.videosPerDay" placeholder="选择发布数量">
                    <el-option
                      v-for="num in 55"
                      :key="num"
                      :label="num"
                      :value="num"
                    />
                  </el-select>
                </div>
                <div class="schedule-item">
                  <span class="label">每天发布时间：</span>
                  <el-time-select
                    v-for="(time, index) in tab.dailyTimes"
                    :key="index"
                    v-model="tab.dailyTimes[index]"
                    start="00:00"
                    step="00:30"
                    end="23:30"
                    placeholder="选择时间"
                  />
                  <el-button
                    v-if="tab.dailyTimes.length < tab.videosPerDay"
                    type="primary"
                    size="small"
                    @click="tab.dailyTimes.push('10:00')"
                  >
                    添加时间
                  </el-button>
                </div>
                <div class="schedule-item">
                  <span class="label">开始天数：</span>
                  <el-select v-model="tab.startDays" placeholder="选择开始天数">
                    <el-option :label="'明天'" :value="0" />
                    <el-option :label="'后天'" :value="1" />
                  </el-select>
                </div>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button size="small" @click="cancelPublish(tab)">取消</el-button>
            <el-button
              size="small"
              type="primary"
              @click="confirmPublish(tab)"
              :loading="tab.publishing || false"
            >
              {{ tab.publishing ? '发布中...' : '发布' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 发布进度对话框 -->
    <PublishProgressDialog
      v-model:visible="publishDialogVisible"
      :tab="publishingTab"
      :accounts="publishingAccounts"
      @done="onPublishDone"
      @relogin-done="onReloginDone"
      @update:visible="onPublishClose"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Upload, Plus, Close, Folder, Picture, VideoCamera, InfoFilled, CircleCheckFilled, CircleCloseFilled, WarningFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { materialApi } from '@/api/material'
import { http } from '@/utils/request'
import { accountApi } from '@/api/account'
import PublishProgressDialog from '@/components/PublishProgressDialog.vue'

// API base URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

// Authorization headers
const authHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

// 当前激活的tab
const activeTab = ref('tab1')

// tab计数器
let tabCounter = 1

// 获取应用状态管理
const appStore = useAppStore()

// 上传相关状态
const uploadOptionsVisible = ref(false)
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const currentUploadTab = ref(null)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)

// 图片预览相关状态
const imagePreviewVisible = ref(false)
const previewImageUrl = ref('')

// 预览图片
const previewImage = (url) => {
  previewImageUrl.value = url
  imagePreviewVisible.value = true
}

// 批量发布相关状态
const batchPublishing = ref(false)
const batchPublishMessage = ref('')
const batchPublishType = ref('info')

// 平台列表 - 对应后端type字段
const platforms = [
  { key: 3, name: '抖音' },
  { key: 4, name: '快手' },
  { key: 2, name: '视频号' },
  { key: 1, name: '小红书' },
  { key: 5, name: '百家号' },
  { key: 6, name: 'TikTok' },
  { key: 7, name: 'Bilibili' }
]

const defaultTabInit = {
  name: 'tab1',
  label: '发布1',
  publishType: 'video', // 发布类型: 'video'=视频发布, 'note'=图文发布
  fileList: [], // 后端返回的文件名列表
  displayFileList: [], // 用于显示的文件列表
  selectedAccounts: [], // 选中的账号ID列表
  selectedPlatform: 1, // 选中的平台（单选）
  title: '',
  desc: '', // 图文正文描述
  productLink: '', // 商品链接
  productTitle: '', // 商品名称
  selectedTopics: [], // 话题列表（不带#号）
  scheduleEnabled: false, // 定时发布开关
  videosPerDay: 1, // 每天发布视频数量
  dailyTimes: ['10:00'], // 每天发布时间点列表
  startDays: 0, // 从今天开始计算的发布天数，0表示明天，1表示后天
  publishStatus: null, // 发布状态，包含message和type
  publishing: false, // 发布状态，用于控制按钮loading效果
  isDraft: false, // 是否保存为草稿，仅视频号平台可见
  isOriginal: false // 是否标记为原创
}

// helper to create a fresh deep-copied tab from defaultTabInit
const makeNewTab = () => {
  // prefer structuredClone when available (newer browsers/node), fallback to JSON
  try {
    return typeof structuredClone === 'function' ? structuredClone(defaultTabInit) : JSON.parse(JSON.stringify(defaultTabInit))
  } catch (e) {
    return JSON.parse(JSON.stringify(defaultTabInit))
  }
}

// tab页数据 - 默认只有一个tab (use deep copy to avoid shared refs)
const tabs = reactive([
  makeNewTab()
])

// 账号相关状态（话题弹窗使用 currentTab）
const currentTab = ref(null)

// 获取账号状态管理
const accountStore = useAccountStore()

// 平台映射
const platformMap = {
  '抖音': 3,
  '视频号': 2,
  '小红书': 1,
  '快手': 4,
  '百家号': 5,
  'TikTok': 6,
  'Bilibili': 7
}
const platformReverseMap = {
  3: '抖音',
  2: '视频号',
  1: '小红书',
  4: '快手',
  5: '百家号',
  6: 'TikTok',
  7: 'Bilibili'
}

// 获取平台标签类型（与账号管理页保持一致）
const getPlatformTagType = (platform) => {
  const typeMap = {
    '快手': 'success',
    '抖音': 'danger',
    '视频号': 'warning',
    '小红书': 'info',
    '百家号': 'primary',
    'TikTok': 'danger',
    'Bilibili': ''
  }
  return typeMap[platform] || 'info'
}

// （账号直接从 accountStore.accounts 获取）

// 根据所选账号自动推导平台
const deducePlatformFromAccounts = (accountIds) => {
  if (!accountIds || accountIds.length === 0) return null
  const firstAccount = accountStore.accounts.find(acc => acc.id === accountIds[0])
  if (!firstAccount) return null
  return platformMap[firstAccount.platform] || null
}

// 统计每个平台下被选中的账号数
const getPlatformAccountCount = (tab, platformKey) => {
  const platformName = platformReverseMap[platformKey]
  if (!platformName) return 0
  return tab.selectedAccounts.filter(accId => {
    const acc = accountStore.accounts.find(a => a.id === accId)
    return acc && acc.platform === platformName
  }).length
}

// 话题相关状态
const topicDialogVisible = ref(false)
const customTopic = ref('')

// 推荐话题列表
const recommendedTopics = [
  '游戏', '电影', '音乐', '美食', '旅行', '文化',
  '科技', '生活', '娱乐', '体育', '教育', '艺术',
  '健康', '时尚', '美妆', '摄影', '宠物', '汽车'
]

// 添加新tab
const addTab = () => {
  tabCounter++
  const newTab = makeNewTab()
  newTab.name = `tab${tabCounter}`
  newTab.label = `发布${tabCounter}`
  tabs.push(newTab)
  activeTab.value = newTab.name
}

// 删除tab
const removeTab = (tabName) => {
  const index = tabs.findIndex(tab => tab.name === tabName)
  if (index > -1) {
    tabs.splice(index, 1)
    // 如果删除的是当前激活的tab，切换到第一个tab
    if (activeTab.value === tabName && tabs.length > 0) {
      activeTab.value = tabs[0].name
    }
  }
}

// 处理文件上传成功
const handleUploadSuccess = (response, file, tab) => {
  if (response.code === 200) {
    // 获取文件路径
    const filePath = response.data.path || response.data
    // 从路径中提取文件名
    const filename = filePath.split('/').pop()
    
    // 保存文件信息到fileList，包含文件路径和其他信息
    const fileInfo = {
      name: file.name,
      url: materialApi.getMaterialPreviewUrl(filename), // 使用getMaterialPreviewUrl生成预览URL
      path: filePath,
      size: file.size,
      type: file.type
    }
    
    // 添加到文件列表
    tab.fileList.push(fileInfo)
    
    // 更新显示列表
    tab.displayFileList = [...tab.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
    
    ElMessage.success('文件上传成功')
  } else {
    ElMessage.error(response.msg || '上传失败')
  }
}

// 处理文件上传失败
const handleUploadError = (error) => {
  ElMessage.error('文件上传失败')
}

// 删除已上传文件
const removeFile = (tab, index) => {
  // 从文件列表中删除
  tab.fileList.splice(index, 1)
  
  // 更新显示列表
  tab.displayFileList = [...tab.fileList.map(item => ({
    name: item.name,
    url: item.url
  }))]
  
  ElMessage.success('文件删除成功')
}

// 话题相关方法
// 打开添加话题弹窗
const openTopicDialog = (tab) => {
  currentTab.value = tab
  topicDialogVisible.value = true
}

// 添加自定义话题
const addCustomTopic = () => {
  if (!customTopic.value.trim()) {
    ElMessage.warning('请输入话题内容')
    return
  }
  if (currentTab.value && !currentTab.value.selectedTopics.includes(customTopic.value.trim())) {
    currentTab.value.selectedTopics.push(customTopic.value.trim())
    customTopic.value = ''
    ElMessage.success('话题添加成功')
  } else {
    ElMessage.warning('话题已存在')
  }
}

// 切换推荐话题
const toggleRecommendedTopic = (topic) => {
  if (!currentTab.value) return
  
  const index = currentTab.value.selectedTopics.indexOf(topic)
  if (index > -1) {
    currentTab.value.selectedTopics.splice(index, 1)
  } else {
    currentTab.value.selectedTopics.push(topic)
  }
}

// 删除话题
const removeTopic = (tab, index) => {
  tab.selectedTopics.splice(index, 1)
}

// 确认添加话题
const confirmTopicSelection = () => {
  topicDialogVisible.value = false
  customTopic.value = ''
  currentTab.value = null
  ElMessage.success('添加话题完成')
}

// 页面加载时自动获取账号列表
onMounted(async () => {
  try {
    const res = await accountApi.getAccounts()
    if (res.code === 200) {
      accountStore.setAccounts(res.data)
    }
  } catch (error) {
    console.error('获取账号列表失败:', error)
  }
})

// 切换账号选择 — 单次点击直接选中/取消，并自动推导平台
const toggleAccount = (tab, accountId) => {
  const index = tab.selectedAccounts.indexOf(accountId)
  if (index > -1) {
    tab.selectedAccounts.splice(index, 1)
  } else {
    tab.selectedAccounts.push(accountId)
    // 自动推导平台
    const deduced = deducePlatformFromAccounts(tab.selectedAccounts)
    if (deduced !== null) {
      tab.selectedPlatform = deduced
    }
  }
}

// 删除选中的账号 — 全部清空后恢复平台可选
const removeAccount = (tab, index) => {
  tab.selectedAccounts.splice(index, 1)
  // 如果账号全部清空，不做平台推导（用户可手动选）
  if (tab.selectedAccounts.length === 0) {
    // 保留当前平台，让用户可以手动切换
  }
}

// 获取账号显示名称
const getAccountDisplayName = (accountId) => {
  const account = accountStore.accounts.find(acc => acc.id === accountId)
  return account ? account.name : accountId
}

// 取消发布
const cancelPublish = (tab) => {
  ElMessage.info('已取消发布')
}

// 确认发布
const confirmPublish = async (tab) => {
  // 防止重复点击
  if (tab.publishing) {
    throw new Error('正在发布中，请稍候...')
  }

  tab.publishing = true

  // 数据验证
  const fileTypeLabel = tab.publishType === 'note' ? '图片' : '视频'
  if (tab.fileList.length === 0) {
    ElMessage.error(`请先上传${fileTypeLabel}文件`)
    tab.publishing = false
    throw new Error(`请先上传${fileTypeLabel}文件`)
  }
  if (!tab.title.trim()) {
    ElMessage.error('请输入标题')
    tab.publishing = false
    throw new Error('请输入标题')
  }
  if (!tab.selectedPlatform) {
    ElMessage.error('请选择发布平台')
    tab.publishing = false
    throw new Error('请选择发布平台')
  }
  if (tab.selectedAccounts.length === 0) {
    ElMessage.error('请选择发布账号')
    tab.publishing = false
    throw new Error('请选择发布账号')
  }

  // 校验选中账号状态
  const selectedAccountObjects = tab.selectedAccounts
    .map(id => accountStore.accounts.find(a => a.id === id))
    .filter(Boolean)

  const abnormalAccounts = selectedAccountObjects.filter(a => a.status === '异常')
  if (abnormalAccounts.length > 0) {
    try {
      await ElMessageBox.confirm(
        `以下账号 cookie 可能已过期，发布可能失败：\n\n${abnormalAccounts.map(a => `  · ${a.name}（${a.platform}）`).join('\n')}\n\n是否继续发布？`,
        '账号状态异常',
        {
          confirmButtonText: '继续发布',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch (_) {
      // 用户取消发布
      tab.publishing = false
      return
    }
  }

  // 构造发布数据的深拷贝快照，传给对话框
  publishingTab.value = {
    publishType: tab.publishType,
    selectedPlatform: tab.selectedPlatform,
    title: tab.title,
    desc: tab.desc || '',
    selectedTopics: [...(tab.selectedTopics || [])],
    fileList: tab.fileList.map(f => ({ ...f })),
    scheduleEnabled: tab.scheduleEnabled,
    videosPerDay: tab.videosPerDay || 1,
    dailyTimes: [...(tab.dailyTimes || ['10:00'])],
    startDays: tab.startDays || 0,
    isOriginal: tab.isOriginal || false,
    isDraft: tab.isDraft || false,
    productLink: tab.productLink?.trim() || '',
    productTitle: tab.productTitle?.trim() || ''
  }
  publishingAccounts.value = selectedAccountObjects

  tab.publishing = false
  publishDialogVisible.value = true
}

// 发布进度对话框完成回调
const onPublishDone = ({ successCount, failCount, results }) => {
  const currentTab = tabs.find(t => t.name === activeTab.value)
  if (!currentTab) return

  if (failCount === 0) {
    // 全部成功，清空当前 tab 数据
    currentTab.fileList = []
    currentTab.displayFileList = []
    currentTab.title = ''
    currentTab.desc = ''
    currentTab.selectedTopics = []
    currentTab.selectedAccounts = []
    currentTab.scheduleEnabled = false
    currentTab.publishStatus = {
      message: '所有账号发布成功',
      type: 'success'
    }
    setTimeout(() => {
      publishDialogVisible.value = false
    }, 1000)
  } else {
    currentTab.publishStatus = {
      message: `发布完成：${successCount} 个成功，${failCount} 个失败`,
      type: successCount > 0 ? 'warning' : 'error'
    }
  }
}

// 发布进度对话框关闭时清理
const onPublishClose = () => {
  publishingTab.value = null
  publishingAccounts.value = []
}

// 重登录成功后刷新账号 Store
const onReloginDone = async () => {
  try {
    const res = await accountApi.getAccounts()
    if (res.code === 200) {
      accountStore.setAccounts(res.data)
    }
  } catch (e) {
    console.error('刷新账号列表失败:', e)
  }
}

// 批量发布内部方法：一次性向所有选中账号发布（保持向后兼容）
const _publishTabBulk = async (tab) => {
  // 表单验证
  const fileTypeLabel = tab.publishType === 'note' ? '图片' : '视频'
  if (tab.fileList.length === 0) throw new Error(`请先上传${fileTypeLabel}文件`)
  if (!tab.title.trim()) throw new Error('请输入标题')
  if (!tab.selectedPlatform) throw new Error('请选择发布平台')
  if (tab.selectedAccounts.length === 0) throw new Error('请选择发布账号')

  const publishData = {
    type: tab.selectedPlatform,
    title: tab.title,
    desc: tab.desc || '',
    tags: tab.selectedTopics,
    fileList: tab.fileList.map(file => file.path),
    accountList: tab.selectedAccounts.map(accountId => {
      const account = accountStore.accounts.find(acc => acc.id === accountId)
      return account ? account.filePath : accountId
    }),
    enableTimer: tab.scheduleEnabled ? 1 : 0,
    videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1,
    dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'],
    startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0,
    category: tab.isOriginal ? 1 : 0,
    productLink: tab.productLink.trim() || '',
    productTitle: tab.productTitle.trim() || '',
    isDraft: tab.isDraft
  }

  const apiEndpoint = tab.publishType === 'note' ? '/postNote' : '/postVideo'
  await http.post(apiEndpoint, publishData)

  tab.publishStatus = {
    message: '发布成功',
    type: 'success'
  }
  tab.fileList = []
  tab.displayFileList = []
  tab.title = ''
  tab.desc = ''
  tab.selectedTopics = []
  tab.selectedAccounts = []
  tab.scheduleEnabled = false
}

// 显示上传选项
const showUploadOptions = (tab) => {
  currentUploadTab.value = tab
  uploadOptionsVisible.value = true
}

// 选择本地上传
const selectLocalUpload = () => {
  uploadOptionsVisible.value = false
  localUploadVisible.value = true
}

// 选择素材库
const selectMaterialLibrary = async () => {
  uploadOptionsVisible.value = false
  
  // 如果素材库为空，先获取素材数据
  if (materials.value.length === 0) {
    try {
      const response = await materialApi.getAllMaterials()
      if (response.code === 200) {
        appStore.setMaterials(response.data)
      } else {
        ElMessage.error('获取素材列表失败')
        return
      }
    } catch (error) {
      console.error('获取素材列表出错:', error)
      ElMessage.error('获取素材列表失败')
      return
    }
  }
  
  selectedMaterials.value = []
  materialLibraryVisible.value = true
}

// 确认素材选择
const confirmMaterialSelection = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('请选择至少一个素材')
    return
  }
  
  if (currentUploadTab.value) {
    // 将选中的素材添加到当前tab的文件列表
    selectedMaterials.value.forEach(materialId => {
      const material = materials.value.find(m => m.id === materialId)
      if (material) {
        const fileInfo = {
          name: material.filename,
          url: materialApi.getMaterialPreviewUrl(material.file_path.split('/').pop()),
          path: material.file_path,
          size: material.filesize * 1024 * 1024, // 转换为字节
          type: 'video/mp4'
        }
        
        // 检查是否已存在相同文件
        const exists = currentUploadTab.value.fileList.some(file => file.path === fileInfo.path)
        if (!exists) {
          currentUploadTab.value.fileList.push(fileInfo)
        }
      }
    })
    
    // 更新显示列表
    currentUploadTab.value.displayFileList = [...currentUploadTab.value.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
  }
  
  const addedCount = selectedMaterials.value.length
  materialLibraryVisible.value = false
  selectedMaterials.value = []
  currentUploadTab.value = null
  ElMessage.success(`已添加 ${addedCount} 个素材`)
}

// 单次发布进度对话框状态
const publishDialogVisible = ref(false)
const publishingTab = ref(null)
const publishingAccounts = ref([])

// 批量发布对话框状态
const batchPublishDialogVisible = ref(false)
const currentPublishingTab = ref(null)
const publishProgress = ref(0)
const publishResults = ref([])
const isCancelled = ref(false)

// 取消批量发布
const cancelBatchPublish = () => {
  isCancelled.value = true
  ElMessage.info('正在取消发布...')
}

// 批量发布方法
const batchPublish = async () => {
  if (batchPublishing.value) return
  
  batchPublishing.value = true
  currentPublishingTab.value = null
  publishProgress.value = 0
  publishResults.value = []
  isCancelled.value = false
  batchPublishDialogVisible.value = true
  
  try {
    for (let i = 0; i < tabs.length; i++) {
      if (isCancelled.value) {
        publishResults.value.push({
          label: tabs[i].label,
          status: 'cancelled',
          message: '已取消'
        })
        continue
      }

      const tab = tabs[i]
      currentPublishingTab.value = tab
      publishProgress.value = Math.floor((i / tabs.length) * 100)

      try {
        await _publishTabBulk(tab)
        publishResults.value.push({
          label: tab.label,
          status: 'success',
          message: '发布成功'
        })
      } catch (error) {
        publishResults.value.push({
          label: tab.label,
          status: 'error',
          message: error.message
        })
        // 不立即返回，继续显示发布结果
      }
    }
    
    publishProgress.value = 100
    
    // 统计发布结果
    const successCount = publishResults.value.filter(r => r.status === 'success').length
    const failCount = publishResults.value.filter(r => r.status === 'error').length
    const cancelCount = publishResults.value.filter(r => r.status === 'cancelled').length
    
    if (isCancelled.value) {
      ElMessage.warning(`发布已取消：${successCount}个成功，${failCount}个失败，${cancelCount}个未执行`)
    } else if (failCount > 0) {
      ElMessage.error(`发布完成：${successCount}个成功，${failCount}个失败`)
    } else {
      ElMessage.success('所有Tab发布成功')
      setTimeout(() => {
        batchPublishDialogVisible.value = false
      }, 1000)
    }
    
  } catch (error) {
    console.error('批量发布出错:', error)
    ElMessage.error('批量发布出错，请重试')
  } finally {
    batchPublishing.value = false
    isCancelled.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.publish-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  
  // Tab管理区域
  .tab-management {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
    padding: 15px 20px;
    
    .tab-header {
      display: flex;
      align-items: flex-start;
      gap: 15px;
      
      .tab-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        flex: 1;
        min-width: 0;
        
        .tab-item {
           display: flex;
           align-items: center;
           gap: 6px;
           padding: 6px 12px;
           background-color: #f5f7fa;
           border: 1px solid #dcdfe6;
           border-radius: 4px;
           cursor: pointer;
           transition: all 0.3s;
           font-size: 14px;
           height: 32px;
           
           &:hover {
             background-color: #ecf5ff;
             border-color: #b3d8ff;
           }
           
           &.active {
             background-color: #409eff;
             border-color: #409eff;
             color: #fff;
             
             .close-icon {
               color: #fff;
               
               &:hover {
                 background-color: rgba(255, 255, 255, 0.2);
               }
             }
           }
           
           .close-icon {
             padding: 2px;
             border-radius: 2px;
             cursor: pointer;
             transition: background-color 0.3s;
             font-size: 12px;
             
             &:hover {
               background-color: rgba(0, 0, 0, 0.1);
             }
           }
         }
       }
       
      .tab-actions {
        display: flex;
        gap: 10px;
        flex-shrink: 0;
        
        .add-tab-btn,
        .batch-publish-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
        }
      }
    }
  }
  
  // 批量发布进度对话框样式
  .publish-progress {
    padding: 20px;
    
    .current-publishing {
      margin: 15px 0;
      text-align: center;
      color: #606266;
    }

    .publish-results {
      margin-top: 20px;
      border-top: 1px solid #EBEEF5;
      padding-top: 15px;
      max-height: 300px;
      overflow-y: auto;

      .result-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: #606266;

        .el-icon {
          margin-right: 8px;
        }

        .label {
          margin-right: 10px;
          font-weight: 500;
        }

        .message {
          color: #909399;
        }

        &.success {
          color: #67C23A;
        }

        &.error {
          color: #F56C6C;
        }

        &.cancelled {
          color: #909399;
        }
      }
    }
  }

  .dialog-footer {
    text-align: right;
  }
  
  // 内容区域
  .publish-content {
    flex: 1;
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;
    
    .tab-content-wrapper {
      display: flex;
      justify-content: center;
      
      .tab-content {
        width: 100%;
        max-width: 800px;
        
        h3 {
          font-size: 16px;
          font-weight: 500;
          color: $text-primary;
          margin: 0 0 10px 0;
        }
        
        .upload-section,
        .account-section,
        .platform-section,
        .publish-type-section,
        .title-section,
        .product-section,
        .topic-section,
        .desc-section,
        .schedule-section {
          margin-bottom: 30px;
        }

        .product-section {
          .product-name-input,
          .product-link-input {
            margin-bottom: 5px;
          }
        }

        .publish-type-section {
          margin-bottom: 30px;

          .publish-type-radios {
            display: flex;
            gap: 20px;

            .publish-type-radio {
              display: flex;
              align-items: center;
              gap: 4px;
            }
          }
        }

        .desc-section {
          margin-bottom: 30px;

          .desc-input {
            max-width: 600px;
          }
        }

        // 文件列表中图片缩略图样式
        .file-item {
          .image-thumbnail-wrapper {
            width: 60px;
            height: 60px;
            flex-shrink: 0;
            margin-right: 10px;
            border-radius: 4px;
            overflow: hidden;
            cursor: pointer;
            border: 1px solid #ebeef5;

            .image-thumbnail {
              width: 100%;
              height: 100%;
              object-fit: cover;
              transition: transform 0.2s;

              &:hover {
                transform: scale(1.1);
              }
            }
          }

          .file-name-text {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-right: 10px;
            color: #606266;
            font-size: 14px;
          }
        }
        
        .video-upload {
          width: 100%;
          
          :deep(.el-upload-dragger) {
            width: 100%;
            height: 180px;
          }
        }
        
        .account-input {
          max-width: 400px;
        }
        
        .platform-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;

          .platform-btn {
            min-width: 80px;
          }
        }

        .platform-count {
          color: #909399;
          font-size: 12px;
          margin-left: 4px;
        }

        .platform-hint {
          margin-top: 8px;
          font-size: 12px;
          color: #909399;
          display: flex;
          align-items: center;
          gap: 4px;
        }

        // 账号选择卡片样式
        .account-display {
          .selected-accounts {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
            min-height: 28px;

            .account-tag {
              font-size: 13px;
            }
          }

          .account-list {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;

            .account-card {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 8px;
              min-width: 140px;
              padding: 10px 14px;
              border: 1px solid #dcdfe6;
              border-radius: 6px;
              background: #fafafa;
              cursor: pointer;
              transition: all 0.2s ease;
              position: relative;

              &:hover {
                border-color: #409eff;
                background: #ecf5ff;
              }

              &.is-selected {
                border-color: #409eff;
                background: #ecf5ff;

                .account-name {
                  color: #409eff;
                  font-weight: 500;
                }
              }

              .account-card-content {
                display: flex;
                align-items: center;
                gap: 8px;
                min-width: 0;

                .account-name {
                  font-size: 14px;
                  color: #303133;
                  white-space: nowrap;
                }
              }

              .check-icon {
                color: #409eff;
                font-size: 16px;
                flex-shrink: 0;
              }
            }
          }
        }

        .platform-mini-tag {
          margin-left: 8px;
          flex-shrink: 0;
        }

        .account-info {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .title-input {
          max-width: 600px;
        }
        
        .topic-display {
          display: flex;
          flex-direction: column;
          gap: 12px;
          
          .selected-topics {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            min-height: 32px;
            
            .topic-tag {
              font-size: 14px;
            }
          }
          
          .select-topic-btn {
            align-self: flex-start;
          }
        }
        
        .schedule-controls {
          display: flex;
          flex-direction: column;
          gap: 15px;

          .schedule-settings {
            margin-top: 15px;
            padding: 15px;
            background-color: #f5f7fa;
            border-radius: 4px;

            .schedule-item {
              display: flex;
              align-items: center;
              margin-bottom: 15px;

              &:last-child {
                margin-bottom: 0;
              }

              .label {
                min-width: 120px;
                margin-right: 10px;
              }

              .el-time-select {
                margin-right: 10px;
              }

              .el-button {
                margin-left: 10px;
              }
            }
          }
        }
        
        .action-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #ebeef5;
        }

        .draft-section {
          margin: 20px 0;

          .draft-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .original-section {
          margin: 10px 0 20px;

          .original-checkbox {
            display: block;
            margin: 10px 0;
          }
        }
      }
    }
  }

  // 已上传文件列表样式
  .uploaded-files {
    margin-top: 20px;
    
    h4 {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #303133;
    }
    
    .file-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      
      .file-item {
        display: flex;
        align-items: center;
        padding: 10px 15px;
        background-color: #f5f7fa;
        border-radius: 4px;
        
        .el-link {
          margin-right: 10px;
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        
        .file-size {
          color: #909399;
          font-size: 13px;
          margin-right: auto;
        }
      }
    }
  }
  
  // 图片预览弹窗样式
  .image-preview-dialog {
    .image-preview-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 200px;
    }
  }

  // 添加话题弹窗样式
  .topic-dialog {
    .topic-dialog-content {
      .custom-topic-input {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
        
        .custom-input {
          flex: 1;
        }
      }
      
      .recommended-topics {
        h4 {
          margin: 0 0 16px 0;
          font-size: 16px;
          font-weight: 500;
          color: #303133;
        }
        
        .topic-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
          gap: 12px;
          
          .topic-btn {
            height: 36px;
            font-size: 14px;
            border-radius: 6px;
            min-width: 100px;
            padding: 0 12px;
            white-space: nowrap;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            
            &.el-button--primary {
              background-color: #409eff;
              border-color: #409eff;
              color: white;
            }
          }
        }
      }
    }
    
    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }
}
</style>
