/**
 * 知识库与 SQL 工具接口。
 * 文件上传与演示数据播种属管理类操作，页面上收入折叠面板，不在主导航展示。
 */
import request from '../utils/request'
import { getToken } from '../utils/auth'

const BASE_URL = '/v1'

/** 初始化 RAG 知识库（建 pgvector 表与索引） */
export function initRag() {
  return request({ url: '/rag/init', method: 'post' })
}

/** 批量文本文档入库：data = { documents: [{ content, source, metadata }] } */
export function ingestDocuments(data) {
  return request({ url: '/rag/documents', method: 'post', data: data })
}

/** 向量检索测试：data = { query, top_k }，返回 { query, results: [{ id, content, source, score }] } */
export function searchRag(data) {
  return request({ url: '/rag/search', method: 'post', data: data })
}

/**
 * 多文件上传入 RAG 知识库（multipart，字段名 files，可选 source 标注来源）。
 * el-upload 每个文件发一次请求，返回 { inserted, files: [{ filename, inserted, skipped, error }] }
 */
export function getUploadConfig() {
  return {
    action: BASE_URL + '/rag/upload',
    headers: { 'Authorization': 'Bearer ' + (getToken() || '') },
    name: 'files',
    data: {}
  }
}

/** 业务表结构摘要（文本） */
export function getSqlSchema() {
  return request({ url: '/tools/sql/schema', method: 'get' })
}

/** 执行只读 SQL：data = { sql }，返回 { sql, columns, rows, row_count, max_rows } */
export function querySql(data) {
  return request({ url: '/tools/sql/query', method: 'post', data: data })
}

/** 播种演示业务数据 */
export function seedDemoData() {
  return request({ url: '/tools/sql/demo-data', method: 'post' })
}
