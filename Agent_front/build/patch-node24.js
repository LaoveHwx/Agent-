// npm install 后自动给 webpack-dev-server 打 Node 24 兼容补丁（幂等，可重复运行）。
// 原理：spdy 内部调用 process.binding('http_parser')，Node 24 已删除该 API，
// 顶层 require('spdy') 会直接崩。项目未启用 https，改为 try/catch 懒加载即可安全绕过。
// 已在 dev/build scripts 里前置执行；重装依赖后无需手动处理。
'use strict'
const fs = require('fs')
const path = require('path')

const target = path.resolve(__dirname, '../node_modules/webpack-dev-server/lib/Server.js')

if (!fs.existsSync(target)) {
  console.log('[patch-node24] node_modules 尚未安装，跳过（请先 npm install）')
  process.exit(0)
}

const original = "const spdy = require('spdy');"
const patched = [
  "// Patched for Node 24+: spdy uses process.binding('http_parser') which was",
  "// removed. Only load it lazily when https is actually enabled.",
  "let spdy;",
  "try {",
  "  spdy = require('spdy');",
  "} catch (e) {",
  "  spdy = { createServer: function() { throw new Error('spdy is not supported on this Node version (https disabled)'); } };",
  "}"
].join('\n')

let code = fs.readFileSync(target, 'utf8')
if (code.indexOf('Patched for Node 24+') >= 0) {
  console.log('[patch-node24] 补丁已存在，跳过')
} else if (code.indexOf(original) >= 0) {
  code = code.replace(original, patched)
  fs.writeFileSync(target, code)
  console.log('[patch-node24] 已修补 Server.js（spdy 懒加载，https 未启用时安全）')
} else {
  console.log('[patch-node24] 未找到预期的 spdy 顶层引用，可能版本不同，跳过')
  console.log('[patch-node24] 若 dev 启动报 http_parser 相关错误，请手动检查该文件')
}
