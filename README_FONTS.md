# 字体增强指南 (Font Enhancement Guide)

Writer Tool 支持加载本地字体文件，无需安装到 Windows 系统目录即可在软件内使用。这对于使用“绿色版”软件或没有管理员权限的用户非常方便。

## 如何添加新字体

1.  找到您的数据目录：`writer_data/` (通常在软件根目录下)。
2.  进入 `fonts` 文件夹（如果没有，请手动创建）。
    *   路径：`writer_data/fonts/`
3.  将 `.ttf` 或 `.otf` 字体文件复制到该文件夹中。
4.  重启软件。
5.  在“设置” -> “外观”或“导出设置”中，您现在可以选择这些新字体了。

## 推荐免费商用中文字体

以下是一些非常适合写作和阅读的开源/免费字体：

### 1. 霞鹜文楷 (LXGW WenKai)
*   **风格**：兼具楷书的韵味和黑体的易读性，非常适合小说创作和屏幕阅读。
*   **适用**：正文、编辑器、PDF导出。
*   **下载**：[GitHub Releases](https://github.com/lxgw/LxgwWenKai/releases) (下载 .ttf 文件)

### 2. 思源黑体 (Source Han Sans / Noto Sans CJK)
*   **风格**：现代、简洁、无衬线。
*   **适用**：UI界面、标题。
*   **下载**：[Google Fonts](https://fonts.google.com/noto/specimen/Noto+Sans+SC)

### 3. 思源宋体 (Source Han Serif / Noto Serif CJK)
*   **风格**：传统、优雅、有衬线。
*   **适用**：正文、印刷风格导出。
*   **下载**：[Google Fonts](https://fonts.google.com/noto/specimen/Noto+Serif+SC)

### 4. 得意黑 (Smiley Sans)
*   **风格**：独特、有设计感、略带倾斜。
*   **适用**：标题、强调文本。
*   **下载**：[GitHub](https://github.com/atelier-anchor/smiley-sans)

## 注意事项

*   **PDF 导出**：为了在导出的 PDF 中正确显示中文，建议将字体文件放入 `writer_data/fonts/` 目录。系统会自动注册它们供导出引擎使用。如果使用系统安装的字体，PDF 导出可能会因为找不到字体文件而回退到默认字体（Courier），导致中文显示为乱码。
*   **文件大小**：中文字体文件通常较大（10MB+），请注意磁盘空间。
