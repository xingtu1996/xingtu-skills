---
name: ardot-effect-fallback
description: 在 Ardot 画布上实现光晕/毛玻璃效果时，若当前 schema 不支持 LAYER_BLUR/BACKGROUND_BLUR，改用 GRADIENT_RADIAL 填充 + 透明度达成柔光。适用于海报、banner、AI 产品揭秘页等需要极光/辉光/玻璃质感的视觉设计任务。
---

# Ardot 柔光/辉光效果回退

## 触发场景
- 需要 `LAYER_BLUR` 或 `BACKGROUND_BLUR` 做光晕/毛玻璃，但 `batch_edit` 返回 `Property "effects" failed validation`，说明当前环境 schema 只接受 `DROP_SHADOW | INNER_SHADOW | TEXTURE | GLASS`。
- 常见于深紫黑底 + 极光流光的 AI 产品海报/hero banner。

## 回退方案

把「模糊光晕」拆成**径向渐变填充**（中心不透明 → 边缘透明）+ 低透明度图层叠加：

```javascript
glow=I(parent, {
  type:"frame", layout:"none",
  x:-160, y:-140, width:760, height:760,
  fills:[{
    type:"GRADIENT_RADIAL",
    gradientStops:[
      {color:{r:0.13,g:0.83,b:1.0,a:0.55}, position:0, boundVariables:{}},
      {color:{r:0.13,g:0.83,b:1.0,a:0}, position:1, boundVariables:{}}
    ],
    gradientTransform:[[0.5,0,0.5],[0,0.5,0.5]],
    opacity:1, visible:true, blendMode:"NORMAL"
  }],
  effects:[]
})
```

## 设计原则
1. **多叠 2–3 层**：青/紫/绿各一层，模拟极光流动；每层用 `GRADIENT_RADIAL`，中心透明度 0.4–0.6。
2. **居下层**：光晕节点先于主体内容插入，保证作为背景装饰，不抢主视觉。
3. **文字永远压得住**：主标题区域避开光晕最强处，或在其上加半透明暗面/玻璃卡片兜底。
4. **仍可用 `DROP_SHADOW`**：主体卡片、按钮可用 `DROP_SHADOW` 做悬浮/描边发光，这是 schema 稳定支持的。

## 效果组合
- **极光背景**：深色底 + 多层径向渐变光晕。
- **玻璃卡片**：半透明填充 `rgba(255,255,255,0.06)` + 细描边 + 高 `cornerRadius`；毛玻璃靠背景本身的光晕/暗面提供，不强求 blur。
- **按钮/标签高亮**：薄荷绿 `#5EEAD4` 描边 + 同色文字，配合半透明填充。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/ardot-effect-fallback -->
