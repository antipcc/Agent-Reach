# WOO — 穿搭记录 App（iOS / SwiftUI）

每天拍一张全身照，自动抠图存成当日 OOTD；AI 把照片拆成单品归进衣橱；勾选单品可以对自己的照片做虚拟换装；还能把一套穿搭重建成**真正的 3D 模型**，在首页卡片上拖拽转身。

- **平台**：iOS 17+，SwiftUI，Swift 5 语言模式
- **界面语言**：全中文，且**不跟随系统语言** —— 日期、月份、星期都固定用中文（见 `Woo/App/Localization.swift`）。
  唯一保留英文的是首页那个巨大的季节水印（SPRING / SUMMER / FALL / WINTER）和字标 WOO，
  它们是平面设计元素不是界面文案
- **架构**：`Woo`（界面层）→ `WooKit`（纯 Foundation 逻辑层，可在任何平台编译和单测）
- **AI**：四个协议 + 一个 composition root，默认全部走离线 Mock；抠图例外，用系统 Vision 真实实现

---

## 1. 跑起来

```bash
cd apps/woo-ios
./bootstrap.sh            # 需要 xcodegen：brew install xcodegen
```

脚本会用 `project.yml` 生成 `Woo.xcodeproj` 并打开。选 iOS 17+ 模拟器或真机，Run。

**没有 XcodeGen 时的手动方案**（30 秒）：

1. Xcode → File → New → Project → iOS App，命名 `Woo`，Interface 选 SwiftUI，最低版本 17.0
2. 删掉模板生成的 `ContentView.swift` 和 `WooApp.swift`
3. 把本目录的 `Woo/` 文件夹整个拖进项目（选 "Create groups"）
4. File → Add Package Dependencies → Add Local → 选本目录的 `WooKit/`，把 `WooKit` 加到 app target
5. Target → Info 里补上 `NSCameraUsageDescription` 和 `NSPhotoLibraryAddUsageDescription`（文案见 `Woo/Info.plist`）

> 工程文件是**生成**的、不入库：`project.yml` 可读可 review、不会产生合并冲突，而手写 `pbxproj` 出一个字符错误就是「项目已损坏」。

### 模拟器注意

模拟器没有摄像头。拍摄页会自动识别并给出「Choose a photo」，走系统相册选图，全流程一样能跑通。

---

## 2. 目录

```
apps/woo-ios/
├── project.yml                 # 工程定义（XcodeGen）
├── bootstrap.sh                # 生成 + 打开工程
├── scripts/check-swift-hygiene.py   # 静态体检（见第 5 节）
├── Woo/                        # 界面层：SwiftUI + 相机 + Vision + CoreImage
│   ├── App/                    Theme · AppEnvironment · LibraryModel · RootView · WooApp
│   ├── Features/               Home · Calendar · Capture · Processing · Wardrobe · DressUp
│   ├── Components/             导航栏 · 底部抽屉 · 药丸按钮 · 配色圆点 · 吐司
│   └── Services/               Vision 抠图 · 配色提取 · Mock 绘图 · 图片加载 · 存相册
└── WooKit/                     逻辑层：只 import Foundation
    ├── Sources/WooKit/Models/  Outfit · GarmentItem · SpinAsset · Season · AssetRef
    ├── Sources/WooKit/Store/   OutfitStore 协议 · FileOutfitStore · LibraryService
    ├── Sources/WooKit/AI/      四个 AI 协议 · AIProvider · Mock · HTTP 实现
    └── Tests/WooKitTests/      模型 / 存储 / 用例层 / Mock 的单测
```

**分层是硬约束**：`WooKit` 不允许 import SwiftUI / UIKit / Vision / AVFoundation。凡是能测的逻辑都在下面，上面只剩视图。体检脚本会强制这条。

---

## 3. 数据存在哪

`Application Support/Woo/`：

```
library.json          # 全部元数据，一次原子写
Assets/cutout-*.png   # 抠好的透明图
Assets/original-*.jpeg
Assets/item-*.png     # 衣橱单品
Assets/spin-*.png     # 360° 帧
```

没有 CoreData / SwiftData —— 纯 Foundation 才能在非 Apple 平台上跑单测。删除一套穿搭会连带删掉它自己的图片，但**衣橱单品会保留**（衣橱比某一天的穿搭活得久）。

---

## 4. 接入真实 AI 模型

现在四个能力里，**抠图是真的**（Vision 端上跑，免费离线），其余三个是 Mock：

| 能力 | 协议 | 现状 |
|---|---|---|
| 抠图 | `BackgroundRemovalService` | ✅ 真实：`VisionBackgroundRemovalService` |
| 单品拆解 | `GarmentExtractionService` | Mock：按人体区域裁切照片 |
| 虚拟换装 | `TryOnService` | Mock：按所选单品配色对照片做色调偏移 |
| **3D 重建** | `ModelGenerationService` | Mock：内置方块人偶（灰色，一眼看出是占位） |
| 360° 帧环（兜底） | `SpinService` | Mock：按余弦横向压缩 + 镜像的转台错觉 |

Mock 的结果**看起来像那么回事，但不是模型产出**，换装结果页会明确标注。

### 换成真实服务

两种方式，二选一，环境变量优先：

**A. 在 app bundle 放 `Woo/AIConfig.plist`**（已 gitignore）：

```xml
<dict>
  <key>BaseURL</key>      <string>https://your-endpoint.example</string>
  <key>APIKey</key>       <string>sk-...</string>
  <key>ModelPath</key>    <string>/v1/image-to-3d</string>
  <key>TryOnPath</key>    <string>/v1/try-on</string>
  <key>GarmentsPath</key> <string>/v1/garments</string>
  <key>SpinPath</key>     <string>/v1/spin</string>
</dict>
```

**B. Scheme 里加环境变量**：`WOO_AI_BASE_URL`、`WOO_AI_API_KEY`、`WOO_AI_MODEL_PATH`、`WOO_AI_TRYON_PATH`、`WOO_AI_GARMENTS_PATH`、`WOO_AI_SPIN_PATH`、`WOO_AI_CUTOUT_PATH`。

**只配了一部分也没关系** —— 没配的那个能力自动继续用 Mock（见 `AIProvider.live(config:fallback:)`），可以一个一个接。

### 3D 重建的接口约定（`ModelPath`）

单图重建都是**异步任务**，所以走「提交 → 轮询 → 下载」三步：

```
POST {baseURL}{ModelPath}          multipart: image=<bytes>
  → {"job_id": "..."}                        # 也支持直接返回模型
GET  {baseURL}{ModelPath}/{job_id}
  → {"status": "pending|succeeded|failed", "progress": 0.42,
     "model_url": "https://...", "format": "usdz"}
GET  {model_url} → 模型字节
```

默认轮询间隔 3s，单个任务预算 600s（`AIConfig.modelPollInterval` / `modelTimeout`）。
服务端报了 `progress` 就用它驱动进度条，没报就按已用时间爬到 90% —— 绝不会假装做完了。

**格式只接受 iOS 能打开的：`usdz` / `obj` / `ply`。** 返回 `glb` / `gltf` 会直接报错并告诉你去要
usdz —— Model I/O 打不开 glTF，与其加载时静默失败，不如提交时就说清楚。

**没配 `ModelPath` 时**会自动退回 `SpinPath` 的帧环；两个都没配就是内置的灰色方块人偶。

### 其它接口约定

`HTTPAIService` 默认按「multipart 上传 → JSON 返回 base64 图」这个最通行的形状写的：

```
POST {baseURL}{path}      Authorization: Bearer {apiKey}
multipart/form-data: image=<bytes> [, garment_0..n=<bytes>]
→ 200 {"images": ["<base64>"], "items": [{"name","category","image"}]}
```

真实服务商的响应形状不同时，**只改 `HTTPAIService` 里的 `decodeImages` / `decodeGarments` 两个方法**，其它任何文件都不用动。

想彻底换掉某个实现（比如自己写个 CoreML 的），写个类型实现对应协议，然后在 `Woo/App/AppEnvironment.swift` 的 `live()` 里换一行即可 —— 那是全 App 唯一决定用哪个实现的地方。

---

## 5. 验证

### 验证状态（截至最近一次提交）

| 项目 | 状态 | 怎么验的 |
|---|---|---|
| `WooKit` 编译 | ✅ **真编译过**，0 error 0 warning | Swift 5.10 / x86_64-linux |
| `WooKit` 单测 | ✅ **43 个用例全过** | `swift test` |
| `Woo`（SwiftUI 层）语法 | ✅ 33 个文件 0 语法错误 | `swiftc -frontend -parse` |
| `Woo`（SwiftUI 层）**类型检查** | ❌ **未验证** | Linux 上没有 SwiftUI/UIKit/Vision，做不到 |
| 静态体检 | ✅ 63 个文件 0 问题 | `check-swift-hygiene.py` |

**这条边界很重要**：SwiftUI 层只过了语法解析，没过类型检查。参数标签写错、协议没实现全、
类型推断失败这类问题，只有你在 Xcode 里第一次 Build 才会暴露。别把上表第三行当成「能编译」。

<details>
<summary>在 Linux 容器里复现上面的编译和单测</summary>

官方 `download.swift.org` 在受限网络里常被拦。SwiftWasm 在 GitHub release 上发布的是
**完整的 Linux 工具链**（host 端就是原生 x86_64 的 swiftc/swiftpm，wasm 只是多带一个 target），
可以直接用来编译和测试 `WooKit`：

```bash
curl -fL -o swift.tar.gz \
  https://github.com/swiftwasm/swift/releases/download/swift-wasm-5.10.0-RELEASE/swift-wasm-5.10.0-RELEASE-ubuntu22.04_x86_64.tar.gz
tar xzf swift.tar.gz
export PATH="$PWD/swift-wasm-5.10.0-RELEASE/usr/bin:$PATH"

cd apps/woo-ios/WooKit && swift test
swiftc -frontend -parse $(find ../Woo -name '*.swift')   # SwiftUI 层只能到语法这一层
```
</details>

### 逻辑层单测

```bash
cd apps/woo-ios/WooKit
swift test                # macOS 上直接跑；也可在 Xcode 里 Cmd+U
```

覆盖：杀进程重开后数据还在、删穿搭不影响衣橱、重复拆解不会产生重复单品、重新生成 360° 会清掉旧帧、进度只增不减且以 1.0 收尾、只配了部分端点时其余保持 Mock。

### 静态体检（不需要编译器）

```bash
python3 apps/woo-ios/scripts/check-swift-hygiene.py
```

检查括号配平、重复声明、分层违规（`WooKit` 碰了 UI 框架）。**它不是编译器**，只是编译前的一张便宜的网。

### 手动验收清单

对着视频逐条过：

- [ ] 首页：左右 ‹ › 翻看不同穿搭；季节水印随日期变（SPRING / SUMMER / FALL / WINTER）
- [ ] 首页：拖拽人物可移动；双击复位
- [ ] 首页：生成过 360° 的穿搭，横向拖拽能转身（没配 API 时转的是灰色方块人偶，这是对的）
- [ ] 底部抽屉：上滑露出该套的单品缩略图和名称
- [ ] 日历：翻月；有穿搭的日子显示缩略图；点击跳回首页对应那套
- [ ] 拍摄：全身取景椭圆 + 提示；拍完（模拟器用相册）自动抠图入库
- [ ] 衣橱：按 上装 / 外套 / 下装 / 鞋履 分组；点选出现顶部托盘
- [ ] 换装：选照片 → 进度文案在过半后变成「快好了，先别退出 App」→ 结果页 ♥ / ↓ / 分享
- [ ] 360°：进度页可 Minimize，收起后底部出现小浮标，仍在跑
- [ ] 中文排版：单品名（`lineLimit(1)`）会不会截断、按钮宽度够不够 —— 这类只有真机能看出来
- [ ] 3D：模型是否**透明底**渲染在白卡片上 —— SceneKit 的透明背景是这次唯一在 Linux 上验证不了的渲染细节
- [ ] 杀掉 App 重开，数据都还在

---

## 6. 已知边界

- **Mock 不是模型**：换装/拆解/3D 的结果是占位效果，接真实端点后自然消失
- **单图重建的天花板**：宽松衣物（纱裙、阔腿裤）是这类模型最弱的一环，背面和面部基本靠脑补。
  这是方案本身的限制，不是实现问题；效果不满意就换供应商，或退回 `SpinPath` 用帧环
- **抠图依赖 iOS 17 Vision**：找不到人像时会退回原图而不是失败（宁可存下来）
- 仅竖屏、仅 iPhone（`TARGETED_DEVICE_FAMILY = 1`）
- 没有账号、没有云同步、没有分享社区
