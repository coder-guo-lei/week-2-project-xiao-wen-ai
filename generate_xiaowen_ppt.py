"""
生成「小文」项目答辩用 PPTX（需安装 python-pptx）。

用法（仓库根目录）:
    pip install python-pptx
    python generate_xiaowen_ppt.py

输出文件与脚本同目录：xiaowen-report-final.pptx（使用 ASCII 文件名避免终端编码导致乱码）
"""
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

_ROOT = Path(__file__).resolve().parent
OUT = str(_ROOT / "xiaowen-report-final.pptx")
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
W, H = prs.slide_width, prs.slide_height
FONT = "Microsoft YaHei"
C = {
    "bg": RGBColor(8, 12, 30), "panel": RGBColor(22, 31, 62),
    "panel2": RGBColor(30, 43, 86), "white": RGBColor(248, 250, 255),
    "muted": RGBColor(174, 190, 225), "cyan": RGBColor(58, 220, 255),
    "blue": RGBColor(74, 144, 255), "purple": RGBColor(155, 92, 255),
    "green": RGBColor(76, 230, 170), "orange": RGBColor(255, 180, 90),
    "pink": RGBColor(255, 92, 180), "red": RGBColor(255, 105, 130)
}
ACC = [C["cyan"], C["blue"], C["purple"], C["green"], C["orange"], C["pink"]]

def fill(s, color, trans=0):
    s.fill.solid(); s.fill.fore_color.rgb = color; s.fill.transparency = trans; s.line.fill.background()

def line(s, color, w=1, trans=0):
    s.line.color.rgb = color; s.line.width = Pt(w); s.line.transparency = trans

def txt(slide, x, y, w, h, text, size=14, color=None, bold=False, align=PP_ALIGN.LEFT):
    b = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.text = text; p.alignment = align
    p.font.name = FONT; p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = color or C["white"]
    return b

def bg(slide):
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H); fill(r, C["bg"])
    for x,y,sz,col,tr in [(10.4,-.5,3.2,C["purple"],55),(-.8,5.2,2.7,C["blue"],65),(5.2,1.1,1.5,C["cyan"],82)]:
        o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(sz), Inches(sz)); fill(o, col, tr)
    for i in range(8):
        ln = slide.shapes.add_connector(1, Inches(.35), Inches(.6+i*.78), Inches(13), Inches(.6+i*.78)); line(ln, RGBColor(40,55,95), .35, 62)

def footer(slide, n):
    txt(slide,.55,7.04,6,.25,"小文智能 APP · AI Voice Assistant Project",8,RGBColor(130,150,195))
    txt(slide,12.25,7.02,.55,.25,f"{n:02d}",10,C["cyan"],True,PP_ALIGN.RIGHT)

def title(slide, t, sub, n):
    bg(slide); txt(slide,.7,.42,8.7,.55,t,28,C["white"],True)
    if sub: txt(slide,.72,1.02,9.6,.34,sub,11.5,C["muted"])
    a=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.72), Inches(1.42), Inches(1.2), Inches(.05)); fill(a,C["cyan"])
    footer(slide,n)

def card(slide,x,y,w,h,t,body,color):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)); fill(s,C["panel"],5); line(s,RGBColor(70,90,145),1,35)
    b=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(.08), Inches(h)); fill(b,color)
    txt(slide,x+.22,y+.12,w-.38,.28,t,13,C["white"],True)
    box=slide.shapes.add_textbox(Inches(x+.22), Inches(y+.55), Inches(w-.42), Inches(h-.65)); tf=box.text_frame; tf.word_wrap=True
    for i,l in enumerate(body.split("\n")):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.text=l; p.font.name=FONT; p.font.size=Pt(10.2); p.font.color.rgb=C["muted"]; p.space_after=Pt(3)

def metric(slide,x,y,v,l,c):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(2.35), Inches(1.02)); fill(s,C["panel2"],4); line(s,c,1.2,12)
    txt(slide,x+.1,y+.12,2.15,.36,v,22,c,True,PP_ALIGN.CENTER); txt(slide,x+.1,y+.62,2.15,.25,l,9.5,C["muted"],False,PP_ALIGN.CENTER)

def chip(slide,x,y,t,c):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(1.58), Inches(.36)); fill(s,c,18); line(s,c,1,8)
    txt(slide,x+.05,y+.03,1.48,.28,t,9.5,C["white"],True,PP_ALIGN.CENTER)

# 1 封面
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
for r,col,tr in [(2.6,C["cyan"],70),(2.05,C["purple"],76),(1.5,C["blue"],82)]:
    o=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9.25+(2.6-r)/2), Inches(1.75+(2.6-r)/2), Inches(r), Inches(r)); o.fill.background(); line(o,col,2,tr)
o=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.05), Inches(2.55), Inches(1), Inches(1)); fill(o,C["cyan"],8); line(o,C["white"],1,35)
txt(s,.78,1.18,7.8,.35,"AI VOICE ASSISTANT · PROJECT REPORT",12,C["cyan"],True)
txt(s,.75,1.68,7.8,.82,"小文智能 APP 项目汇报",38,C["white"],True)
txt(s,.8,2.58,7.5,.55,"集 AI 对话、语音交互、天气查询、音乐播放、文生图、数据可视化与桌面控制于一体的智能助手原型",16,C["muted"])
for i,(t,c) in enumerate([("React + Vite",C["blue"]),("Flask API",C["green"]),("DashScope / DeepSeek",C["purple"]),("SVG + zhdate",C["cyan"])]): chip(s,.82+i*1.82,3.38,t,c)
txt(s,.82,6.25,4,.3,"汇报人：刘汉文    日期：2026",11,RGBColor(150,166,210)); footer(s,1)

# 2 目录
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"目录","从项目定位到落地实现，再到问题复盘与后续规划",2)
items=[("01","项目定位与应用场景"),("02","应用方式、方法与核心数据"),("03","系统架构与技术实现"),("04","工作亮点"),("05","问题与改进"),("06","下季度计划与感谢")]
for i,(no,t) in enumerate(items):
    y=1.72+i*.78; txt(s,.9,y,.55,.3,no,15,C["cyan"],True,PP_ALIGN.CENTER); txt(s,1.65,y,5,.3,t,16,C["white"],True)
    ln=s.shapes.add_connector(1,Inches(1.55),Inches(y+.42),Inches(11.8),Inches(y+.42)); line(ln,RGBColor(55,73,120),.5,45)

# 3 项目定位
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"项目定位：面向个人桌面的 AI 智能助手","通过自然语言和语音交互，把 AI 能力转化为日常可用的应用入口",3)
card(s,.75,1.7,3.75,1.55,"用户侧价值","一句话完成查询、播放、生成、翻译和打开应用\n降低操作门槛，强化语音助手体验",C["cyan"])
card(s,4.8,1.7,3.75,1.55,"产品侧价值","将多个 AI 与生活服务能力汇聚到统一界面\n形成可演示、可扩展、可迭代的 App 原型",C["purple"])
card(s,8.85,1.7,3.75,1.55,"技术侧价值","覆盖前端组件化、后端 API、模型调用、异步任务\n适合作为课程设计、项目展示和 AI 应用样板",C["green"])
txt(s,.85,4.0,11.8,.36,"核心定位：不是单一聊天机器人，而是一个可执行任务的 AI 智能应用入口。",19,C["white"],True,PP_ALIGN.CENTER)
for i,(t,b,c) in enumerate([("生活助手","天气 / 音乐 / 问答",C["blue"]),("创作助手","AI 对话 / 文生图",C["purple"]),("数据助手","文本/文件生成图表",C["cyan"]),("桌面助手","打开应用 / 快捷操作",C["green"])]): card(s,1.15+i*2.9,4.78,2.35,.95,t,b,c)

# 4 方法数据
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"应用方式、实现方法与核心数据","用户一句自然语言指令，系统自动完成意图识别、能力调用和结果展示",4)
for i,(t,b,c) in enumerate([("输入","文字 / 语音 / 文件 / 示例指令",C["cyan"]),("识别","关键词规则 + 模式判断",C["blue"]),("调用","AI / 天气 / 音乐 / 图片 / 图表 / 本机应用",C["purple"]),("反馈","卡片展示 + 图表 + 日志 + 朗读",C["green"])]):
    card(s,.85+i*3.05,1.62,2.55,1.12,t,b,c)
metric(s,.95,3.45,"15+","已实现核心功能点",C["cyan"]); metric(s,3.65,3.45,"4+","后端核心 API",C["green"]); metric(s,6.35,3.45,"12+","前端组件模块",C["purple"]); metric(s,9.05,3.45,"80","单图表最大数据点",C["orange"])
card(s,.95,5.08,3.75,1.1,"前端实现","React + Vite\n组件化界面 + localStorage 状态持久化\nWeb Speech API 语音识别与朗读",C["blue"])
card(s,4.9,5.08,3.75,1.1,"后端实现","Flask + Flask-CORS\n统一 /api/send-task 指令入口\nrequests 调用第三方服务",C["green"])
card(s,8.85,5.08,3.55,1.1,"数据实现","文本正则解析 + CSV / Excel 文件读取\nSVG 折线图 / 柱状图\n摘要统计与表格预览",C["purple"])

# 5 架构
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"系统架构：前后端分离 + 多服务能力编排","以统一指令入口连接多个 AI 与工具服务",5)
for i,(t,b,c) in enumerate([("用户交互层","文字输入\n语音识别\n文件上传\n示例指令\n划词工具",C["cyan"]),("前端展示层","ChatPanel\nWeatherCard\nMusicPlayer\nImagePreview\nChartPanel / XiaowenBot",C["blue"]),("后端调度层","Flask API\nparse_command\n图表解析\n时间与农历注入\n白名单应用启动",C["green"]),("外部能力层","DashScope / DeepSeek\n文生图 / VL\n高德天气\n网易云搜索\nWindows 应用",C["purple"])]): card(s,.75+i*3.1,1.65,2.62,3.85,t,b,c)
txt(s,1.0,6.15,11.5,.38,"设计思路：前端负责体验和展示，后端负责安全调度与第三方能力调用，统一返回 type 字段驱动页面组件切换。",15,C["white"],True,PP_ALIGN.CENTER)

# 6 亮点
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"工作亮点","能执行任务 + 时间与农历可信（服务端注入事实，减少模型编造）",6)
h=[("01 多轮对话能力","支持连续追问：先问承德美食，再追问这些在哪能吃到。"),("02 AI 多能力集成","DashScope 为主、DeepSeek 可选兜底；文生图、翻译、天气、音乐、图表统一入口。"),("03 数据可视化能力","文本或 CSV / Excel 自动生成折线图、柱状图；无数据时可演示数据兜底。"),("04 时间与农历可信","LOCAL_TIMEZONE + zhdate：公历「此刻」与农历锚点写入提示，阴历生日换算有据可查。"),("05 异步文生图体验","任务提交后轮询状态，前端展示生成进度。"),("06 安全桌面控制","白名单启动本机应用；组件化与 Hook 拆分便于扩展。")]
for i,(t,b) in enumerate(h): card(s,.8+(i%2)*6.1,1.58+(i//2)*1.55,5.65,1.18,t,b,ACC[i])

# 7 问题改进
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"问题与改进","当前版本已能演示核心能力，但仍需要从稳定性、智能化和工程化继续提升",7)
rows=[("意图识别","关键词规则为主","引入大模型意图分类，减少误判"),("图表能力","当前单系列为主","扩展多系列、饼图和导出图片/PDF"),("音乐播放","受版权和外链限制","增加多结果选择、合法音乐源和失败重试"),("时间与农历","模型易编造日期 / 阴历","已接入服务端注入 + zhdate；持续校验闰月等边界"),("后端结构","功能集中在 app.py","拆分 services、utils、config 模块"),("部署形态","本地开发模式","关闭 debug，增加生产配置和日志监控")]
for i,(a,b,c) in enumerate(rows):
    y=1.75+i*.86; card(s,.85,y,2.3,.58,a,"",ACC[i%6]); txt(s,3.45,y+.08,3.1,.25,b,11,C["muted"]); txt(s,7.0,y+.08,5.3,.25,c,11,C["muted"])

# 8 下季度计划
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"下季度计划","围绕“更智能、更稳定、更可展示、更可扩展”推进下一阶段迭代",8)
plans=[("第 1 阶段\n体验增强","完善多轮记忆\n自动朗读开关\n优化默认示例\n增强错误提示",C["cyan"]),("第 2 阶段\n能力扩展","日程 / 备忘录\n图片历史与下载\n多系列图表\n联网搜索入口",C["purple"]),("第 3 阶段\n工程优化","后端服务模块化\n图表服务拆分\n日志和错误码\n生产环境配置",C["green"]),("第 4 阶段\n部署展示","Docker 或云部署\nHTTPS / Nginx\n演示脚本\n完善答辩材料",C["orange"])]
for i,(t,b,c) in enumerate(plans): card(s,.8+i*3.05,1.75,2.65,3.65,t,b,c)
txt(s,1.0,6.08,11.2,.35,"目标：从“本地可运行的 AI 助手原型”升级为“可持续迭代、可部署展示的智能应用平台”。",16,C["white"],True,PP_ALIGN.CENTER)

# 9 演示路径
s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,"建议演示路径","用一条完整用户路径展示小文智能 APP 的能力闭环",9)
demos=[("1. 语音唤醒","说“小文小文”，进入指令识别"),("2. 生活查询","询问“承德天气怎么样”"),("3. 连续对话","先问承德美食，再追问位置"),("4. 数据图表","生成折线图 一月:120 二月:180 三月:150"),("5. AI 创作","说“画一只水彩小猫”"),("6. 桌面控制","说“打开计算器”")]
for i,(t,b) in enumerate(demos): card(s,.95+(i%3)*4.05,1.65+(i//3)*2.0,3.45,1.35,t,b,ACC[i])
txt(s,1.0,6.05,11.2,.4,"演示重点：让观众看到小文不是静态页面，而是可以理解指令、调用能力并完成任务的 AI 应用。",15,C["white"],True,PP_ALIGN.CENTER)

# 10 感谢
s=prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
txt(s,.9,1.65,11.5,.65,"感谢聆听",42,C["white"],True,PP_ALIGN.CENTER)
txt(s,1.45,2.55,10.4,.5,"小文智能 APP 将继续向更自然、更稳定、更具执行力的个人 AI 助手演进",18,C["muted"],False,PP_ALIGN.CENTER)
for i,(t,c) in enumerate([("能听",C["cyan"]),("能说",C["blue"]),("能聊",C["purple"]),("能画",C["pink"]),("能看",C["orange"]),("能开",C["green"])]): chip(s,1.45+i*1.65,3.55,t,c)
txt(s,3.0,5.05,7.3,.45,"Q&A",28,C["cyan"],True,PP_ALIGN.CENTER); footer(s,10)

prs.save(OUT)
print(OUT)
