import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

const isOffline = process.env.OFFLINE === "true";

const config: Config = {
  title: "KARURA — AI駆動開発 総合ソリューション",
  tagline: "成果物を生成・更新する仕組み一式(スキル・テンプレート・共通規約)",
  // ローカルプレビュー前提のため暫定値。ドキュメントサイトを公開する場合は
  // 配信先(GitHub Pages / S3 等)のホスティング URL に差し替える(sitemap/canonical にのみ影響)
  url: "https://example.com",
  baseUrl: "/",
  // S3 静的ホスティングはクリーンURL(スラッシュなし)を index.html に解決できず
  // 404 になるため、全ルートを /path/ 形式にして /path/index.html を返せるようにする
  trailingSlash: true,
  favicon: "img/favicon.png",
  onBrokenLinks: "warn",
  onBrokenMarkdownLinks: "warn",
  future: {
    experimental_router: isOffline ? "hash" : "browser",
  },
  i18n: {
    defaultLocale: "ja",
    locales: ["ja"],
  },
  markdown: {
    mermaid: true,
    format: "detect",
  },

  presets: [
    [
      "classic",
      {
        docs: {
          path: "docs",
          routeBasePath: "/",
          sidebarPath: "./sidebars.ts",
          exclude: ["**/*.tsv", "**/*.drawio", "**/system-test/**", "**/EMPTY.md"],
        },
        blog: false,
      } satisfies Preset.Options,
    ],
  ],


  themes: [
    "@docusaurus/theme-mermaid",
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        hashed: true,
        language: ["ja", "en"],
        indexBlog: false,
        docsRouteBasePath: "/",
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: "KARURA",
      items: [
        {
          type: "docSidebar",
          sidebarId: "docs",
          label: "Docs",
          position: "left",
        },
      ],
    },
    footer: {
      style: "dark",
      copyright: `© ${new Date().getFullYear()} Acceler Digital LLC. Licensed under Apache License 2.0`,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
