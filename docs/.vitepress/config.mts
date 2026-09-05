import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  lang: 'zh-CN',
  title: 'Agent Deep Research',
  titleTemplate: '九家 Agent 实现思想对比',
  description:
    'Agent Infra 知识地图：以 Claude Code / Codex / Grok / DeepSeek / OpenCode / Pi / Claw / Qwen-Agent / Hermes 九家实现为教材，每章按「论文脉络 → 原理深潜 → 源码对证 → 权衡结论 → 未来方向」五段式展开',

  // GitHub Pages 项目站点 https://<org>.github.io/agent-deep-research/
  base: '/agent-deep-research/',

  lastUpdated: true,
  cleanUrls: true,

  head: [['meta', { name: 'theme-color', content: '#5672cd' }]],

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: '/favicon.svg',

    nav: [
      { text: '首页', link: '/' },
      { text: '前言', link: '/preface' },
      { text: '一页纸速查', link: '/ch09-one-pager' },
      { text: '学习路径', link: '/ch10-roadmap' },
    ],

    sidebar: [
      { text: '前言', link: '/preface' },
      {
        text: '0 使用者入口',
        collapsed: false,
        items: [{ text: '第0章 从你的使用经验出发', link: '/ch00-user-phenomena' }],
      },
      {
        text: 'I 入门：公共知识',
        collapsed: false,
        items: [
          { text: '第1章 全景与定位', link: '/ch01-landscape' },
          { text: '第2章 公共模型：六件套', link: '/ch02-common-model' },
        ],
      },
      {
        text: 'II 原理：分组件精读',
        collapsed: false,
        items: [
          { text: '第3章 Agent Loop 精读', link: '/ch03-loop' },
          { text: '第4章 Tool / 权限 / 沙箱', link: '/ch04-tools' },
          { text: '第5章 Context 工程', link: '/ch05-context' },
          { text: '第6章 Memory 深潜：从 MemGPT 到 A-MEM', link: '/ch05b-memory' },
          { text: '第7章 Session / Trace / 持久化', link: '/ch06-session' },
          { text: '第8章 模型抽象与多 Provider', link: '/ch07-model' },
          { text: '第9章 多 Agent 与任务规划', link: '/ch08-multi-agent' },
        ],
      },
      {
        text: 'III 工程：可靠性与可观测',
        collapsed: false,
        items: [
          { text: '第10章 可观测性与评测', link: '/ch09-observability' },
          { text: '第11章 安全、可靠性与自愈', link: '/ch10-reliability' },
        ],
      },
      {
        text: 'IV 成长：精深学习与速查',
        collapsed: false,
        items: [
          { text: '第12章 精深学习路径：四阶段动手路线', link: '/ch10-roadmap' },
          { text: '第13章 一页纸速查', link: '/ch09-one-pager' },
        ],
      },
      {
        text: 'V 综合：思想与展望',
        collapsed: false,
        items: [{ text: '第14章 Harness 思想总纲：九家设计哲学', link: '/ch14-harness-philosophy' }],
      },
      {
        text: 'VI 理论底座（原 agent-infra-research）',
        collapsed: true,
        items: [
          { text: 'T0 导读：这份研究从哪来', link: '/theory/preface' },
          { text: 'T1 Agent Infra 全景概览', link: '/theory/chapter-01-landscape' },
          { text: 'T2 Agent Memory 架构深度分析', link: '/theory/chapter-02-memory' },
          { text: 'T3 Context Engineering', link: '/theory/chapter-03-context' },
          { text: 'T4 Agent Runtime 设计模式', link: '/theory/chapter-04-runtime' },
          { text: 'T5 行业趋势与岗位分析', link: '/theory/chapter-05-industry' },
          { text: 'T6 开源生态与技术栈', link: '/theory/chapter-06-ecosystem' },
          { text: 'T7 研究计划与学习路径', link: '/theory/chapter-07-roadmap' },
          { text: '附录 TA 已验证的研究发现', link: '/theory/appendix-a' },
          { text: '附录 TB 被否决的观点及原因', link: '/theory/appendix-b' },
          { text: '附录 TC 参考来源清单', link: '/theory/appendix-c' },
          { text: '附录 TD Agent Safety 与 Federated Memory', link: '/theory/appendix-d' },
          { text: '附录 TE 多模态 Memory 与端侧推理', link: '/theory/appendix-e' },
        ],
      },
      {
        text: '附录',
        collapsed: true,
        items: [
          { text: '附录 A 术语表', link: '/appendix-glossary' },
          { text: '附录 B 源码索引与锚点', link: '/appendix-sources' },
          { text: '附录 C 理论卷（卷 VI）衔接与阅读路径', link: '/appendix-bridge' },
          { text: '附录 D 中间调研落盘', link: '/appendix-research-log' },
          { text: '附录 E 论文与文献索引', link: '/appendix-papers' },
        ],
      },
    ],

    outline: {
      level: [2, 3],
      label: '本页大纲',
    },

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
          modal: {
            noResultsText: '无法找到相关结果',
            resetButtonTitle: '清除查询条件',
            footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' },
          },
        },
      },
    },

    editLink: {
      pattern: 'https://github.com/Atituiset/agent-deep-research/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页',
    },

    socialLinks: [{ icon: 'github', link: 'https://github.com/Atituiset/agent-deep-research' }],

    docFooter: { prev: '上一页', next: '下一页' },

    lastUpdatedText: '最后更新于',
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式',
    skipToContentLabel: '跳转到内容',

    footer: {
      message: '基于 MIT 许可发布',
      copyright: 'Copyright © 2026 agent-deep-research',
    },
  },
})
