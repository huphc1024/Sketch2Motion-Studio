![Sketch to Motion 预览](asset/preview.gif)

# Sketch to Motion

[English](README.md) | [简体中文](README.zh-CN.md)

## 彩色版本演示

| 输入图片 | 彩色绘制动画 |
|:---:|:---:|
| <img src="asset/demo_input.png" width="420"> | <img src="asset/demo_color.gif" width="420"> |

使用彩色处理流程生成：

```bash
python sketch2svg_color.py input.png 16
python render_color.py input_color.svg --duration 5.0 --delay 0.05 --scale 3.55 --output-file output
```

彩色处理流程会将图片量化为最多 16 种颜色，用 potrace 分别描摹每个颜色图层，并使用 Manim 渲染彩色绘制动画。生成的 SVG 自带背景色，因此可单独移动或分享，无需配套文件。

本项目使用 [Manim](https://www.manim.community/) 将静态图片转换为流畅的绘制动画。

它可以接收涂鸦、照片或草图，将其转换为 SVG 矢量图，并用 Manim 渲染为 MP4 动画视频。项目还会把最后一帧添加到视频开头，形成短暂定格，使成片的开场更自然。

---

## 功能

- **图片 -> 线稿 -> SVG -> 动画 MP4**
- 可调整的动画参数：
  - **动画时长**（秒）
  - **子路径延迟比例**（子路径间的间隔比例）
  - **缩放比例**（放大/缩小）
  - **绘制风格**（`linear`、`smooth`、`there_and_back`、`wiggle`）
  - **视频格式**：横屏 16:9（`1920x1080`）或竖屏 9:16（`1080x1920`）
- 由 Manim 提供高质量矢量渲染
- 可选保留原图颜色的 SVG 和视频生成
- 自动将最后一帧添加到开头，获得更自然的片头
- 提供中英文可切换的 [Gradio](https://www.gradio.app/) Web 界面

---

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/sketch-to-motion.git
cd Sketch2Motion
```

### 2. 安装 Python 依赖

请确保已安装 **Python 3.9+**。

```bash
pip install -r requirements.txt
```

主要依赖：

* [Gradio](https://www.gradio.app/)
* [Manim](https://docs.manim.community/)
* [ffmpeg](https://ffmpeg.org/)（必须安装并加入 PATH）
* [Potrace](https://potrace.sourceforge.net/)（必须安装并加入 PATH）

安装 Manim：

[安装 Manim](https://docs.manim.community/en/stable/installation/uv.html)

安装 ffmpeg：

* **Windows**：[从官方网站下载](https://ffmpeg.org/download.html)，并将 `bin` 文件夹加入 PATH
* **macOS**：`brew install ffmpeg`
* **Linux**：`sudo apt install ffmpeg`，或使用对应的包管理器

安装 Potrace：

* **macOS**：`brew install potrace`
* **Linux**：`sudo apt install potrace`，或使用对应的包管理器

---

## 使用方法

### 启动 Gradio 应用

```bash
python app.py
```

在浏览器中访问：

```
http://127.0.0.1:7880
```

### Web 界面操作流程

1. 使用 **Language / 语言** 下拉菜单，在 English 和中文之间切换。
2. 上传涂鸦或照片作为**输入图片**。如需使用彩色处理流程，请启用**保留颜色**并选择调色板颜色数量。
3. 点击**生成线稿**，将图片转换为 SVG。
4. 调整**动画时长**、**子路径延迟比例**、**缩放比例**和**绘制风格**。
5. 选择**视频格式**（默认横屏），然后点击**生成视频**以渲染和预览动画。
6. 下载生成的 MP4 文件。
