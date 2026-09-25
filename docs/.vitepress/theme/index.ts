import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import DocMeta from './DocMeta.vue'
import Lightbox from './Lightbox.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      'doc-top': () => h(DocMeta),
      'layout-bottom': () => h(Lightbox),
    }),
}
