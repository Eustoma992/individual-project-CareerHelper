<p align="center">
  <img src="docs/banner.svg" alt="大学生实习&校招笔面试数据分析辅导工具" width="100%">
</p>

<p align="center">
  <a href="../../actions/workflows/deploy.yml"><img alt="Pages" src="../../actions/workflows/deploy.yml/badge.svg"></a>
  <a href="../../actions/workflows/ci.yml"><img alt="CI" src="../../actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-1F4E79">
  <img alt="Vanilla JS" src="https://img.shields.io/badge/Frontend-纯静态%20·%20零依赖-2E75B6">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-4472C4">
</p>

<p align="center">
  <b>真实面经统计 → 出题 / 模拟面试 → 量化复盘</b><br>
  纯静态网站：访客打开链接即可使用，无需注册、无需登录、无需安装任何环境。
</p>

---

## 目录

- [这是什么](#这是什么)
- [功能一览](#功能一览)
- [快速开始](#快速开始)
- [AI 能力说明](#ai-能力说明)
- [部署上线](#部署上线)
- [目录结构](#目录结构)
- [数据与题库维护](#数据与题库维护)
- [测试](#测试)
- [常见问题](#常见问题)
- [免责声明与许可](#免责声明与许可)

## 这是什么

校招备考真正的难点，不是「没有题可刷」，而是**不知道目标岗位到底考什么**：考点怎么分布、单选和案例题各占多少、面试官最爱问哪几道、初面和终面考察重点有什么不同。

本项目先从公开求职社区（牛客网、Codetop、职题库、赛码网、应届生求职网等）采集笔面经并整理成**岗位考情画像**，再以这些统计结果约束出题与提问。整站为**纯前端静态站点**（HTML/CSS/原生 JS，零第三方依赖），推送到 GitHub 后由 GitHub Pages 自动部署，**任何人打开链接即可使用**——没有 Streamlit 登录页，没有服务端，练习数据全部保存在访问者自己的浏览器里。

覆盖岗位（16 个）：

| 方向 | 岗位 |
|---|---|
| 互联网 / 计算机 | 后端开发工程师、前端开发工程师、数据分析师、算法工程师、产品经理 |
| 财会 / 审计 | 会计（财务岗）、审计师（事务所）、金融分析师 |
| 银行中后台 | 银行管培生（中后台）、风险管理岗、授信审批岗（公司信贷）、运营清算岗、合规与反洗钱岗 |
| 券商 | 投资银行岗、固定收益岗、财富管理与机构销售岗 |

## 功能一览

| 模块 | 能做什么 | 实现 |
|---|---|---|
| 📊 **岗位数据看板** | 考点分布条形图、题型配比环形图、专业面/行为面高频题与频次、面经关键词、初复终三轮重点 | 原生 SVG 图表（零依赖） |
| ✍️ **笔试模拟** | 内置 **192 道**笔试题（按各岗位考点权重与题型配比生成，含答案解析），按题型配比抽题组卷；客观题即时判分，主观题按参考答案要点估分 | 全部离线可用 |
| 🎤 **面试模拟** | 初/复/终三轮、按高频题提问、追问；**语音作答**（浏览器语音识别）与**题目朗读**（浏览器语音合成）；逐题评估与回放 | Web Speech API |
| 📈 **备考复盘** | 正确率趋势折线、考点掌握度雷达、练习历史，可导出 Markdown 报告 | localStorage + SVG |
| ⚙️ **AI 增强（可选）** | 访客填入自己的 DeepSeek Key 后解锁：AI 现场出题、深度点评（逻辑/覆盖/建议/高分要点）、真实追问 | fetch 直连 DeepSeek API |

设计原则：

- **打开就能用**：不配置任何东西也能完成看板 → 刷题 → 面试 → 复盘全流程。
- **统计先行**：组卷严格贴合各岗位的考点占比与题型配比，而不是随机抽题。
- **隐私**：练习记录只存 `localStorage`；语音识别用浏览器原生能力；唯一会出网的是可选的 AI 调用。
- **手机可用**：响应式布局 + PWA（manifest + Service Worker 离线缓存）。

## 快速开始

**方式一：直接用（推荐）** —— 部署后访问 GitHub Pages 地址即可，见下方[部署上线](#部署上线)。

**方式二：本地预览**（直接双击 index.html 也可以，但建议起个本地服务）：

```bash
cd 本仓库目录
python -m http.server 8080
# 打开 http://localhost:8080
```

**方式三：Streamlit 桌面版（可选）**

仓库同时保留了功能等价的 Streamlit 版本（`app.py` + `pages/`，含本地 whisper 语音转写），适合想跑 Python、需要服务端录音转写或改造成多用户后端的场景：

```bash
pip install -r requirements.txt
streamlit run app.py     # API Key 配置见 .streamlit/secrets.toml.example
```

## AI 能力说明

| 能力 | 不填 Key | 填入自己的 DeepSeek Key |
|---|---|---|
| 岗位看板、内置题库刷题、本地估分 | ✅ | ✅ |
| 面试提问、浏览器语音识别、朗读 | ✅ | ✅ |
| 面试评估 | 本地规则评估（长度/结构/岗位关键词/量化，标注“仅供参考”） | AI 深度点评 |
| 面试追问 | 规则化追问（针对回答缺数字/缺例子的真实追问） | AI 生成追问 |
| 笔试出题 | 内置 192 题按配比组卷 | AI 按考情现场出题 |

Key 在页面右上角 ⚙ 设置，只保存在访客本机的 localStorage，随每次 AI 调用直连 DeepSeek，不经过任何中间服务器。

> **为什么不在代码里内置 Key？** 公开仓库里的 Key 会被爬虫批量抓取盗刷（上一版项目就把 Key 写在了前端数据文件里，属于高风险做法）。本项目的模式保证：不填 Key 功能完整，填了才有 AI 增强。

## 部署上线

仓库内置 `.github/workflows/deploy.yml`，**推送即自动部署**：

1. 把本仓库推送到 GitHub（`main` 分支）；
2. 打开仓库 **Settings → Pages → Source**，选择 **GitHub Actions**（首次需要）；
3. 之后每次 push，Actions 会自动构建并发布；
4. 访问 `https://<你的用户名>.github.io/<仓库名>/`。

上线前记得把 `index.html` 里的 3 处 `https://github.com` 占位链接（页脚「GitHub 仓库」、首页「查看源码」）换成你的仓库地址。

<details>
<summary><b>部署到其他静态托管（Vercel / Netlify / 服务器）</b></summary>

整个站点就是仓库根目录的静态文件，任意静态托管把根目录当站点根即可；需要 SPA 回退时可把 404 指到 `index.html`（本站用 hash 路由，通常无需配置）。
</details>

## 目录结构

```text
job-prep/
├── index.html            # 应用入口（单页应用，hash 路由五个视图）
├── style.css             # 全部样式（响应式，蓝色系主题）
├── app.js                # 应用逻辑：路由/看板/笔试/面试/复盘/设置/语音/AI
├── charts.js             # 零依赖 SVG 图表（条形/环形/雷达/折线）
├── data.js               # 打包后的岗位画像 + 内置题库（由脚本生成）
├── manifest.json         # PWA 清单
├── service-worker.js     # 离线缓存（核心资源 cache-first）
├── assets/               # PWA 图标
├── docs/banner.svg       # README 头图
├── data/
│   ├── seed_data.json    # 16 个岗位的考情画像（源数据）
│   └── questions.json    # 内置笔试题库（源数据）
├── scripts/              # 维护脚本（见下节）
├── app.py / pages/ / modules/   # Streamlit 桌面版（可选，功能等价）
├── tests/                # Streamlit 版冒烟测试（pytest）
└── .github/workflows/    # ci.yml（测试）+ deploy.yml（GitHub Pages）
```

## 数据与题库维护

| 命令 | 作用 |
|---|---|
| `python scripts/add_positions.py` / `add_positions2.py` | 向 `seed_data.json` 追加岗位画像（幂等） |
| `python scripts/build_question_bank.py` | 调 DeepSeek 为缺失岗位生成 12 道笔试题（`--force` 全量重生成；需环境变量 `DEEPSEEK_API_KEY`） |
| `python scripts/build_static_data.py` | 把画像 + 题库打包成前端使用的 `data.js` |
| `python scripts/make_icons.py` | 重新生成 PWA 图标 |

改完数据记得重跑 `build_static_data.py` 并提交 `data.js`。

## 测试

- **静态站 E2E**（本地开发用，需要本机 Edge/Chrome）：`npm i puppeteer-core` 后运行 `node scripts/e2e_static.js`，脚本会自动走完「看板 → 组卷 → 交卷 → 面试 → 追问 → 总结 → 复盘」全流程并截图到 `.e2e/`。
- **Streamlit 版**：`pip install -r requirements-dev.txt && pytest -q`（数据自洽性 + 页面渲染 + 无 Key 提示），由 `ci.yml` 在 push/PR 时自动执行。

## 常见问题

<details>
<summary><b>语音识别按钮提示不支持？</b></summary>

浏览器语音识别依赖 Web Speech API：Chrome / Edge 桌面端与 Android Chrome 支持最好；iOS Safari 支持有限。不支持时可直接打字作答，朗读功能（speechSynthesis）在多数浏览器可用。
</details>

<details>
<summary><b>AI 出题/评估报错？</b></summary>

检查右上角 ⚙ 里的 Key 是否以 sk- 开头、账户是否有余额；DeepSeek 接口直连浏览器（已确认支持跨域），若公司网络拦截了 api.deepseek.com 也会失败，可换网络重试。失败时面试评估会自动降级为本地评估。
</details>

<details>
<summary><b>换设备 / 清缓存后记录没了？</b></summary>

记录保存在浏览器 localStorage，不跨设备同步。重要复盘请用「导出 Markdown 报告」留存。
</details>

<details>
<summary><b>能加新岗位吗？</b></summary>

可以。向 `data/seed_data.json` 按现有结构追加岗位，跑 `build_question_bank.py` 生成题库，再跑 `build_static_data.py` 打包即可，页面无需改代码。
</details>

## 免责声明与许可

- 本项目为学习与研究用途的校招备考辅助工具，不提供任何企业内部招聘信息，不构成求职结果承诺。
- 岗位画像与内置题库由公开面经整理并经 AI 生成，占比与频次是体现考察权重的整理估算，请以官方招聘公告与企业实际要求为准。
- 请自行遵守目标网站的服务条款与 robots.txt；仓库不含任何抓取语料与个人隐私数据。
- 代码以 [MIT License](LICENSE) 开源，欢迎 Issue 与 PR。
