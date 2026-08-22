# WOO — 穿搭记录 App（iOS / SwiftUI）

每天拍一张全身照，自动抠图存成当日 OOTD；AI 把照片拆成单品归进衣橱；勾选单品可以对自己的照片做虚拟换装；还能把一套穿搭生成可拖拽旋转的 360° 立体形象。

- **平台**：iOS 17+，SwiftUI，Swift 5 语言模式
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
| 360° | `SpinService` | Mock：按余弦横向压缩 + 镜像的转台错觉 |

Mock 的结果**看起来像那么回事，但不是模型产出**，换装结果页会明确标注。

### 换成真实服务

两种方式，二选一，环境变量优先：

**A. 在 app bundle 放 `Woo/AIConfig.plist`**（已 gitignore）：

```xml
<dict>
  <key>BaseURL</key>      <string>https://your-endpoint.example</string>
  <key>APIKey</key>       <string>sk-...</string>
  <key>TryOnPath</key>    <string>/v1/try-on</string>
  <key>GarmentsPath</key> <string>/v1/garments</string>
  <key>SpinPath</key>     <string>/v1/spin</string>
</dict>
```

**B. Scheme 里加环境变量**：`WOO_AI_BASE_URL`、`WOO_AI_API_KEY`、`WOO_AI_TRYON_PATH`、`WOO_AI_GARMENTS_PATH`、`WOO_AI_SPIN_PATH`、`WOO_AI_CUTOUT_PATH`。

**只配了一部分也没关系** —— 没配的那个能力自动继续用 Mock（见 `AIProvider.live(config:fallback:)`），可以一个一个接。

### 接口约定

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
- [ ] 首页：生成过 360° 的穿搭，横向拖拽能转身
- [ ] 底部抽屉：上滑露出该套的单品缩略图和名称
- [ ] 日历：翻月；有穿搭的日子显示缩略图；点击跳回首页对应那套
- [ ] 拍摄：全身取景椭圆 + 提示；拍完（模拟器用相册）自动抠图入库
- [ ] 衣橱：按 TOPS / OUTERWEAR / BOTTOMS / SHOES 分组；点选出现顶部托盘
- [ ] 换装：选照片 → 进度文案在过半后变成 "Keep the app open..." → 结果页 ♥ / ↓ / 分享
- [ ] 360°：进度页可 Minimize，收起后底部出现小浮标，仍在跑
- [ ] 杀掉 App 重开，数据都还在

---

## 6. 已知边界

- **Mock 不是模型**：换装/拆解/360° 的结果是占位效果，接真实端点后自然消失
- **抠图依赖 iOS 17 Vision**：找不到人像时会退回原图而不是失败（宁可存下来）
- 仅竖屏、仅 iPhone（`TARGETED_DEVICE_FAMILY = 1`）
- 没有账号、没有云同步、没有分享社区
