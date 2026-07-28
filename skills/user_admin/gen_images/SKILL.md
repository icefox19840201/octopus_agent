---
name: gen-images
version: 1.0.0
description: |
  AI图像生成技能，根据文本描述生成高质量图像。
  使用豆包Seedream模型，支持提示词优化，图片保存到 static/images 目录，返回HTML img标签。
allowed-tools:
  - Read
  - Write
  - RunCommand
  - AskUserQuestion
---

# AI图像生成技能

根据用户提供的文本描述，使用AI模型生成高质量图像。

## 核心功能

1. **智能提示词优化**
   
   - 自动优化用户描述，生成高质量图像提示词
   - 支持跳过优化，直接使用原始描述

2. **多种图像尺寸**
   
   - **1024x1024**（默认，正方形 1:1）
   - **1024x1536**（竖屏 2:3）
   - **1536x1024**（横屏 3:2）

3. **自动保存图片**
   
   - 图片默认保存到 `static/images` 目录
   - 自动生成带时间戳的文件名

4. **HTML img标签返回**
   
   - 返回 `<img>` 标签，src 指向保存的图片路径
   - 支持在网页中直接显示

## 工作流程

1. **接收任务**
   
   - 获取用户图像描述
   - 确认图像尺寸要求

2. **生成图像**
   
   - 优化提示词（可选）
   - 调用图像生成API
   - 下载并保存图片到 static/images

3. **返回结果**
   
   - 输出 HTML img 标签，src 为 `/static/images/xxx.png`

## 脚本使用说明

使用 `scripts/gen_image.py` 脚本生成图像：

### 基本用法

```bash
python scripts/gen_image.py "图像描述"
```

### 完整参数

```bash
python scripts/gen_image.py "图像描述" [选项]

选项:
  --size {1024x1024,1024x1536,1536x1024,1:1,2:3,3:2}
                        图像尺寸 (默认: 1024x1024)
                        - 1024x1024 或 1:1 = 正方形
                        - 1024x1536 或 2:3 = 竖屏
                        - 1536x1024 或 3:2 = 横屏
  --output-dir, -o OUTPUT_DIR
                        图片保存目录（默认: static/images）
  --no-optimize         禁用提示词优化
  --base64              返回 base64 编码的图片（默认返回文件路径）
```

### 使用示例

#### 示例1：生成基础图像（默认1024x1024，保存到 static/images）

```bash
python scripts/gen_image.py "一只胖橘猫在阳光房里晒太阳，温馨治愈风格"
```

**默认尺寸**：1024x1024（正方形）

返回：

```html
<img src="/static/images/20250602_153045_一只胖橘猫在阳光房.png" alt="一只胖橘猫在阳光房里晒太阳，温馨治愈风格" style="max-width:100%;height:auto;" />
```

#### 示例2：指定尺寸

```bash
python scripts/gen_image.py "未来城市夜景，霓虹灯闪烁" --size 1024x1024
```

**注意**：如果不指定 `--size` 参数，默认使用 `1024x1024` 尺寸。

#### 示例3：指定保存目录

```bash
python scripts/gen_image.py "山水画风格的樱花" --output-dir ./my_images
```

#### 示例4：跳过提示词优化

```bash
python scripts/gen_image.py "exact prompt here" --no-optimize
```

#### 示例5：返回 base64 编码（不保存文件）

```bash
python scripts/gen_image.py "赛博朋克风格" --base64
```

## 返回格式

脚本默认返回 HTML `<img>` 标签，格式如下：

```html
<img src="/static/images/20250602_153045_描述前缀.png" 
     alt="图像描述" 
     style="max-width:100%;height:auto;" />
```

**文件名格式：** `YYYYMMDD_HHMMSS_描述前缀.png`

**你必须：**

1. 完整保留返回的 HTML 标签
2. 不要修改 src 路径
3. 直接将标签嵌入到回复中显示图片
4. 确保 static/images 目录可以通过 Web 访问

## 使用场景

### 场景1：根据描述生成图像（默认1024x1024）

用户：帮我生成一张"赛博朋克风格的城市街道"的图片

执行：

```bash
python scripts/gen_image.py "赛博朋克风格的城市街道，霓虹灯，雨夜，未来感"
```

**说明**：不指定 `--size` 时，默认生成 1024x1024 尺寸的图片。

返回：

```html
<img src="/static/images/20250602_153120_赛博朋克风格的城市街道.png" alt="赛博朋克风格的城市街道，霓虹灯，雨夜，未来感" style="max-width:100%;height:auto;" />
```

### 场景2：生成特定尺寸的头像

用户：生成一张1024x1024的卡通风格头像

执行：

```bash
python scripts/gen_image.py "可爱的卡通头像，大眼睛，微笑" --size 1024x1024
```

### 场景3：批量生成并保存到指定目录

用户：生成几张风景图保存到 ./landscapes 目录

执行：

```bash
python scripts/gen_image.py "壮丽的雪山日出风景" --output-dir ./landscapes
python scripts/gen_image.py "宁静的湖泊倒影" --output-dir ./landscapes
```

## 注意事项

- 图片默认保存到项目根目录的 `static/images/` 文件夹
- 文件名包含时间戳，避免重复
- 确保 `static/images` 目录有写入权限
- 确保 Web 服务器配置了 `/static` 路径的静态文件服务
- 图像生成需要一定时间，请耐心等待
- 提示词优化会调用文本模型，会增加响应时间
- 网络不稳定时可能会超时，可稍后重试
