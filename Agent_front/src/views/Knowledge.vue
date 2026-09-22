<template>
  <div class="knowledge-container">
    <div class="knowledge-header">
      <div>
        <h1>知识库与数据管理</h1>
        <span class="header-sub">文档入库、检索测试与业务表查询</span>
      </div>
      <div class="header-actions">
        <el-button type="text" icon="el-icon-chat-dot-round" @click="$router.push('/chat')">
          返回对话
        </el-button>
        <el-button type="text" icon="el-icon-switch-button" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </div>

    <div class="knowledge-body">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- ========== 知识库管理 ========== -->
        <el-tab-pane label="知识库管理" name="rag">
          <div class="toolbar">
            <el-button size="small" icon="el-icon-set-up" @click="handleInitRag">
              初始化知识库表
            </el-button>
            <span class="toolbar-tip">首次使用 RAG 前先初始化（建 pgvector 表与索引）</span>
          </div>

          <el-divider content-position="left">文本文档入库</el-divider>
          <div v-for="(doc, index) in docList" :key="index" class="doc-row">
            <el-input
              v-model="doc.source"
              placeholder="来源标注（可选，如：销售制度.pdf）"
              class="doc-source"
              size="small"
            ></el-input>
            <el-input
              v-model="doc.content"
              type="textarea"
              :rows="3"
              placeholder="文档内容：业务口径、指标定义、制度说明等"
              class="doc-content"
              size="small"
            ></el-input>
            <el-button
              size="small"
              type="danger"
              icon="el-icon-delete"
              circle
              :disabled="docList.length === 1"
              @click="docList.splice(index, 1)"
            ></el-button>
          </div>
          <div class="doc-actions">
            <el-button size="small" icon="el-icon-plus" @click="docList.push({ content: '', source: '' })">
              再加一条
            </el-button>
            <el-button size="small" type="primary" :loading="ingesting" @click="handleIngest">
              批量入库
            </el-button>
          </div>

          <el-divider content-position="left">检索测试</el-divider>
          <div class="search-row">
            <el-input
              v-model="searchForm.query"
              placeholder="输入查询文本，测试向量检索效果"
              size="small"
              class="search-input"
              @keyup.enter.native="handleSearch"
            ></el-input>
            <span class="topk-label">Top-K</span>
            <el-slider v-model="searchForm.top_k" :min="1" :max="20" class="topk-slider"></el-slider>
            <el-button size="small" type="primary" :loading="searching" @click="handleSearch">
              检索
            </el-button>
          </div>
          <div v-for="item in searchResults" :key="item.id" class="search-result">
            <div class="result-head">
              <el-tag size="mini" type="success">score {{ formatScore(item.score) }}</el-tag>
              <span class="result-source">{{ item.source || '未知来源' }}</span>
            </div>
            <div class="result-content">{{ item.content }}</div>
          </div>
        </el-tab-pane>

        <!-- ========== SQL 工具 ========== -->
        <el-tab-pane label="SQL 工具" name="sql">
          <el-divider content-position="left">业务表结构</el-divider>
          <div class="toolbar">
            <el-button size="small" icon="el-icon-refresh" @click="loadSchema">刷新表结构</el-button>
          </div>
          <pre class="schema-box">{{ schemaSummary || '点击"刷新表结构"加载' }}</pre>

          <el-divider content-position="left">只读 SQL 查询</el-divider>
          <el-input
            v-model="sqlForm.sql"
            type="textarea"
            :rows="4"
            placeholder="仅允许 SELECT / WITH 只读查询，例如：SELECT region, SUM(amount) FROM biz_sales_orders GROUP BY region"
          ></el-input>
          <div class="doc-actions">
            <el-button size="small" type="primary" :loading="querying" @click="handleQuerySql">
              执行查询
            </el-button>
          </div>
          <div v-if="sqlResult" class="sql-result">
            <div class="result-head">
              <span>共 {{ sqlResult.row_count }} 行（上限 {{ sqlResult.max_rows }}）</span>
            </div>
            <el-table :data="sqlResult.rows" size="mini" border stripe max-height="360">
              <el-table-column
                v-for="col in sqlResult.columns"
                :key="col"
                :prop="col"
                :label="col"
                min-width="120"
              ></el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- ========== 高级操作（默认收起，不在主页面显式展示） ========== -->
        <el-tab-pane name="advanced">
          <span slot="label">
            <i class="el-icon-more"></i> 高级操作
          </span>
          <el-collapse v-model="expandedAdvanced">
            <el-collapse-item name="upload">
              <template slot="title">
                <i class="el-icon-upload2 collapse-icon"></i>
                文件上传入知识库（.txt / .md / .pdf 等文本文件）
              </template>
              <el-upload
                class="upload-box"
                drag
                multiple
                :action="uploadConfig.action"
                :headers="uploadConfig.headers"
                :name="uploadConfig.name"
                :data="{ source: uploadSource }"
                :on-success="handleUploadSuccess"
                :on-error="handleUploadError"
                :before-upload="beforeUpload"
              >
                <i class="el-icon-upload"></i>
                <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
                <div class="el-upload__tip" slot="tip">
                  上传后自动解析切分并向量化入库；来源标注（可选）：
                  <el-input v-model="uploadSource" size="mini" class="upload-source-input" placeholder="如：2024销售制度"></el-input>
                </div>
              </el-upload>
            </el-collapse-item>
            <el-collapse-item name="seed">
              <template slot="title">
                <i class="el-icon-data-line collapse-icon"></i>
                播种演示业务数据
              </template>
              <div class="seed-box">
                <p class="seed-tip">向业务库写入一套演示数据（销售订单等），用于快速体验问答效果。</p>
                <el-button size="small" type="warning" :loading="seeding" @click="handleSeed">
                  播种演示数据
                </el-button>
                <div v-if="seedResult" class="seed-result">
                  <el-tag size="small" type="success">{{ seedResult.status }}</el-tag>
                  <span v-for="(count, table) in seedResult.rows" :key="table" class="seed-table">
                    {{ table }}: {{ count }} 行
                  </span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script>
import {
  initRag, ingestDocuments, searchRag, getUploadConfig,
  getSqlSchema, querySql, seedDemoData
} from '../api/knowledge'
import { clearLogin } from '../utils/auth'

export default {
  name: 'Knowledge',
  data() {
    return {
      activeTab: 'rag',
      // 文档入库
      docList: [{ content: '', source: '' }],
      ingesting: false,
      // 检索测试
      searchForm: { query: '', top_k: 5 },
      searching: false,
      searchResults: [],
      // SQL
      schemaSummary: '',
      sqlForm: { sql: '' },
      querying: false,
      sqlResult: null,
      // 高级操作
      expandedAdvanced: [],
      uploadSource: '',
      seeding: false,
      seedResult: null
    }
  },
  computed: {
    uploadConfig() {
      return getUploadConfig()
    }
  },
  methods: {
    formatScore(score) {
      if (score === null || score === undefined) return '-'
      return Number(score).toFixed(4)
    },
    handleLogout() {
      clearLogin()
      this.$router.push('/login')
    },
    // ---- RAG ----
    async handleInitRag() {
      try {
        const res = await initRag()
        this.$message.success('知识库初始化完成（维度 ' + (res.embedding_dim || '-') + '）')
      } catch (e) {
        // 拦截器已提示
      }
    },
    async handleIngest() {
      const documents = this.docList
        .map(d => ({ content: (d.content || '').trim(), source: (d.source || '').trim() || null }))
        .filter(d => d.content)
      if (!documents.length) {
        this.$message.warning('请至少填写一条文档内容')
        return
      }
      this.ingesting = true
      try {
        const res = await ingestDocuments({ documents: documents })
        this.$message.success('成功入库 ' + res.inserted + ' 条文档')
        this.docList = [{ content: '', source: '' }]
      } catch (e) {
        // 拦截器已提示
      } finally {
        this.ingesting = false
      }
    },
    async handleSearch() {
      const query = (this.searchForm.query || '').trim()
      if (!query) {
        this.$message.warning('请输入检索文本')
        return
      }
      this.searching = true
      try {
        const res = await searchRag({ query: query, top_k: this.searchForm.top_k })
        this.searchResults = res.results || []
        if (!this.searchResults.length) {
          this.$message.info('未检索到相关文档，请先入库或调整查询')
        }
      } catch (e) {
        // 拦截器已提示
      } finally {
        this.searching = false
      }
    },
    // ---- SQL ----
    async loadSchema() {
      try {
        const res = await getSqlSchema()
        this.schemaSummary = res.schema_summary || ''
        if (!this.schemaSummary) {
          this.$message.info('未读取到业务表结构，可能需要先播种演示数据')
        }
      } catch (e) {
        // 拦截器已提示
      }
    },
    async handleQuerySql() {
      const sql = (this.sqlForm.sql || '').trim()
      if (!sql) {
        this.$message.warning('请输入 SQL 语句')
        return
      }
      this.querying = true
      try {
        this.sqlResult = await querySql({ sql: sql })
      } catch (e) {
        this.sqlResult = null
      } finally {
        this.querying = false
      }
    },
    // ---- 高级操作 ----
    beforeUpload(file) {
      const isLt50M = file.size / 1024 / 1024 < 50
      if (!isLt50M) {
        this.$message.error('文件大小不能超过 50MB')
      }
      return isLt50M
    },
    handleUploadSuccess(response) {
      // el-upload 不走 axios 拦截器，直接拿后端原始响应
      if (response && response.files) {
        const failed = response.files.filter(f => f.error)
        if (failed.length) {
          this.$message.warning('部分文件入库失败：' + failed[0].filename + ' ' + (failed[0].error || ''))
        } else {
          this.$message.success('上传成功，共入库 ' + response.inserted + ' 条文档分片')
        }
      } else {
        this.$message.error('上传响应格式异常')
      }
    },
    handleUploadError() {
      this.$message.error('上传失败，请确认后端服务已启动')
    },
    async handleSeed() {
      this.seeding = true
      try {
        this.seedResult = await seedDemoData()
        this.$message.success('演示数据播种完成')
      } catch (e) {
        this.seedResult = null
      } finally {
        this.seeding = false
      }
    }
  }
}
</script>

<style scoped>
.knowledge-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f3f6fb;
}

.knowledge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 32px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e5eaf3;
  box-shadow: 0 10px 30px rgba(31, 41, 55, 0.05);
  z-index: 10;
}

.knowledge-header h1 {
  color: #111827;
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px;
}

.header-sub {
  color: #909399;
  font-size: 13px;
}

.knowledge-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.knowledge-body >>> .el-tabs {
  max-width: 980px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-tip {
  font-size: 12px;
  color: #9ca3af;
}

.doc-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.doc-source {
  width: 240px;
  flex-shrink: 0;
}

.doc-content {
  flex: 1;
}

.doc-actions {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  flex: 1;
}

.topk-label {
  font-size: 13px;
  color: #6b7280;
}

.topk-slider {
  width: 140px;
}

.search-result {
  background: #fff;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 10px;
}

.result-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.result-source {
  font-size: 12px;
  color: #6b7280;
}

.result-content {
  font-size: 13px;
  color: #374151;
  line-height: 1.6;
  white-space: pre-wrap;
}

.schema-box {
  background: #0f172a;
  color: #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  font-size: 12px;
  line-height: 1.7;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.sql-result {
  margin-top: 12px;
}

.upload-box {
  max-width: 520px;
}

.upload-source-input {
  width: 200px;
  margin-left: 8px;
}

.collapse-icon {
  margin-right: 6px;
}

.seed-box {
  padding: 4px 0 8px;
}

.seed-tip {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 10px;
}

.seed-result {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.seed-table {
  font-size: 13px;
  color: #374151;
}
</style>
