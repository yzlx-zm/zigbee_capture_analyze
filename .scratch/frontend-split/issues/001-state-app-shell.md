# 1 — state.js + app.js + index.html 壳

**要构建的内容**：创建前端模块化基础层。`state.js`（9 个 export 符号：S/A/sb/fmtTs/sr/setProg/doPI/doI/tsStartEnd）作为所有页面的共享模块。`app.js`（reg/rt/hashchange）作为路由引擎。`index.html` 改为 ES 模块壳（`<script type="module">` 加载 app.js），删除原有全局变量声明，保留导航栏和 #mc 容器。

**阻塞于**：无——可立即开始

**验证方式**：
- F12 控制台：`import('./js/state.js').then(m=>console.log(Object.keys(m)))` 输出 9 个符号
- 导入页文件上传 + 本地路径导入均正常
- 导入结果显示 + 切页恢复正常
- 5 个 hash 路由均可正常进入（页面内容可能暂未迁移，但路由不报错）

**状态**：ready

- [ ] `js/state.js` — 9 个 export 符号从 index.html 提取
- [ ] `js/app.js` — reg()/rt()/hashchange 从 index.html 提取，import state.js
- [ ] `index.html` — 删除全局变量声明，加 `<script type="module" src="js/app.js">`
- [ ] 原全局 S/A/sb/fmtTs/sr/setProg/doPI/doI/tsStart/tsEnd 声明从 index.html 删除
- [ ] 其余 4 个 reg('...') 回调暂留 index.html（后续工单迁移）
