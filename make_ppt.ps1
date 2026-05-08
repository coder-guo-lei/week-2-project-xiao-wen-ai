$out='D:\Desktop\xiaowen\小文智能APP项目汇报.pptx'
$pp=New-Object -ComObject PowerPoint.Application
$pp.Visible=[Microsoft.Office.Core.MsoTriState]::msoTrue
$prs=$pp.Presentations.Add()
$prs.PageSetup.SlideWidth=960
$prs.PageSetup.SlideHeight=540
$blank=12
function RGB($r,$g,$b){ return $r + ($g*256) + ($b*65536) }
$bg=RGB 8 12 30; $panel=RGB 24 34 68; $white=RGB 245 248 255; $muted=RGB 176 190 225
$cyan=RGB 58 220 255; $blue=RGB 74 144 255; $purple=RGB 155 92 255; $green=RGB 76 230 170; $orange=RGB 255 180 90; $pink=RGB 255 92 180
$acc=@($cyan,$blue,$purple,$green,$orange,$pink)
$footerColor=RGB 130 150 195; $authorColor=RGB 150 166 210; $lineColor=RGB 72 92 145
function T($s,$x,$y,$w,$h,$txt,$size,$color,$bold=0,$align=1){$o=$s.Shapes.AddTextbox(1,$x,$y,$w,$h);$r=$o.TextFrame.TextRange;$r.Text=$txt;$r.Font.Name='Microsoft YaHei';$r.Font.Size=$size;$r.Font.Color.RGB=$color;$r.Font.Bold=$bold;$r.ParagraphFormat.Alignment=$align;$o.TextFrame.WordWrap=-1;return $o}
function Bg($s){$r=$s.Shapes.AddShape(1,0,0,960,540);$r.Fill.ForeColor.RGB=$bg;$r.Line.Visible=0;$o=$s.Shapes.AddShape(9,748,-45,230,230);$o.Fill.ForeColor.RGB=$purple;$o.Fill.Transparency=.55;$o.Line.Visible=0;$o=$s.Shapes.AddShape(9,-55,382,190,190);$o.Fill.ForeColor.RGB=$blue;$o.Fill.Transparency=.68;$o.Line.Visible=0;$o=$s.Shapes.AddShape(9,390,78,100,100);$o.Fill.ForeColor.RGB=$cyan;$o.Fill.Transparency=.82;$o.Line.Visible=0}
function Footer($s,$n){T $s 38 508 420 18 '小文智能 APP · AI Voice Assistant Project' 7 (RGB 130 150 195) 0 1|Out-Null;T $s 884 506 40 18 ([string]::Format('{0:d2}',$n)) 9 $cyan 1 3|Out-Null}
function Title($s,$t,$sub,$n){Bg $s;T $s 50 30 650 42 $t 25 $white 1 1|Out-Null;T $s 52 76 720 26 $sub 10 $muted 0 1|Out-Null;$a=$s.Shapes.AddShape(1,52,104,86,4);$a.Fill.ForeColor.RGB=$cyan;$a.Line.Visible=0;Footer $s $n}
function Card($s,$x,$y,$w,$h,$head,$body,$color){$c=$s.Shapes.AddShape(5,$x,$y,$w,$h);$c.Fill.ForeColor.RGB=$panel;$c.Fill.Transparency=.04;$c.Line.ForeColor.RGB=RGB 72 92 145;$b=$s.Shapes.AddShape(1,$x,$y,6,$h);$b.Fill.ForeColor.RGB=$color;$b.Line.Visible=0;T $s ($x+16) ($y+10) ($w-28) 24 $head 12 $white 1 1|Out-Null;T $s ($x+16) ($y+42) ($w-26) ($h-48) $body 9.2 $muted 0 1|Out-Null}
function Metric($s,$x,$y,$v,$lab,$color){$m=$s.Shapes.AddShape(5,$x,$y,170,74);$m.Fill.ForeColor.RGB=RGB 30 43 86;$m.Line.ForeColor.RGB=$color;T $s ($x+8) ($y+8) 154 28 $v 20 $color 1 2|Out-Null;T $s ($x+8) ($y+45) 154 18 $lab 8.5 $muted 0 2|Out-Null}
function Chip($s,$x,$y,$txt,$color){$c=$s.Shapes.AddShape(5,$x,$y,114,26);$c.Fill.ForeColor.RGB=$color;$c.Fill.Transparency=.18;$c.Line.ForeColor.RGB=$color;T $s ($x+4) ($y+5) 106 16 $txt 8.5 $white 1 2|Out-Null}
# 1
$s=$prs.Slides.Add(1,$blank);Bg $s;T $s 56 82 560 28 'AI VOICE ASSISTANT · PROJECT REPORT' 11 $cyan 1 1|Out-Null;T $s 54 120 600 62 '小文智能 APP 项目汇报' 34 $white 1 1|Out-Null;T $s 58 188 560 44 '集 AI 对话、语音交互、天气查询、音乐播放、文生图、划词翻译与桌面控制于一体的智能助手原型' 14 $muted 0 1|Out-Null;Chip $s 60 250 'React + Vite' $blue;Chip $s 190 250 'Flask API' $green;Chip $s 320 250 'DashScope' $purple;Chip $s 450 250 'Web Speech' $cyan;T $s 60 450 330 20 '汇报人：刘汉文    日期：2026' 10 (RGB 150 166 210) 0 1|Out-Null;Footer $s 1
# 2
$s=$prs.Slides.Add(2,$blank);Title $s '目录' '从项目定位到落地实现，再到问题复盘与后续规划' 2;$items=@('项目定位与应用场景','应用方式、方法与核心数据','系统架构与技术实现','工作亮点','问题与改进','下季度计划与感谢');for($i=0;$i -lt $items.Count;$i++){T $s 70 (125+$i*58) 48 24 ([string]::Format('{0:d2}',$i+1)) 14 $cyan 1 2|Out-Null;T $s 140 (125+$i*58) 470 24 $items[$i] 15 $white 1 1|Out-Null}
# 3
$s=$prs.Slides.Add(3,$blank);Title $s '项目定位：面向个人桌面的 AI 智能助手' '通过自然语言和语音交互，把 AI 能力转化为日常可用的应用入口' 3;Card $s 54 125 270 112 '用户侧价值' "一句话完成查询、播放、生成、翻译和打开应用`n降低操作门槛，强化语音助手体验" $cyan;Card $s 346 125 270 112 '产品侧价值' "将多个 AI 与生活服务能力汇聚到统一界面`n形成可演示、可扩展、可迭代的 App 原型" $purple;Card $s 638 125 270 112 '技术侧价值' "覆盖前端组件化、后端 API、模型调用、异步任务`n适合作为课程设计、项目展示和 AI 应用样板" $green;T $s 70 286 820 30 '核心定位：不是单一聊天机器人，而是一个可执行任务的 AI 智能应用入口。' 17 $white 1 2|Out-Null;Card $s 82 350 170 70 '生活助手' '天气 / 音乐 / 问答' $blue;Card $s 292 350 170 70 '创作助手' 'AI 对话 / 文生图' $purple;Card $s 502 350 170 70 '语音助手' '识别 / 唤醒 / 朗读' $cyan;Card $s 712 350 170 70 '桌面助手' '打开应用 / 快捷操作' $green
# 4
$s=$prs.Slides.Add(4,$blank);Title $s '应用方式、实现方法与核心数据' '用户一句自然语言指令，系统自动完成意图识别、能力调用和结果展示' 4;Card $s 62 126 184 82 '输入' '文字 / 语音 / 示例指令' $cyan;Card $s 282 126 184 82 '识别' '关键词规则 + 模式判断' $blue;Card $s 502 126 184 82 '调用' 'AI / 天气 / 音乐 / 图片 / 本机应用' $purple;Card $s 722 126 184 82 '反馈' '卡片展示 + 日志 + 朗读' $green;Metric $s 70 255 '12+' '已实现核心功能点' $cyan;Metric $s 270 255 '3' '后端核心 API' $green;Metric $s 470 255 '10+' '前端组件模块' $purple;Metric $s 670 255 '12' '最近对话上下文条数' $orange;Card $s 70 390 250 78 '前端实现' "React + Vite`n组件化界面 + localStorage`nWeb Speech API" $blue;Card $s 355 390 250 78 '后端实现' "Flask + Flask-CORS`n/api/send-task 统一入口`nrequests 调用第三方服务" $green;Card $s 640 390 250 78 'AI 实现' "DashScope 对话模型`nDashScope 文生图任务`n多轮上下文 messages" $purple
# 5
$s=$prs.Slides.Add(5,$blank);Title $s '系统架构：前后端分离 + 多服务能力编排' '以统一指令入口连接多个 AI 与工具服务' 5;Card $s 54 125 190 280 '用户交互层' "文字输入`n语音识别`n唤醒词`n示例指令`n划词工具" $cyan;Card $s 276 125 190 280 '前端展示层' "ChatPanel`nWeatherCard`nMusicPlayer`nImagePreview`nLogPanel / ModeBar" $blue;Card $s 498 125 190 280 '后端调度层' "Flask API`nparse_command`n意图路由`n上下文管理`n白名单应用启动" $green;Card $s 720 125 190 280 '外部能力层' "DashScope 大模型`nDashScope 文生图`n高德天气`n网易云搜索`nWindows 应用" $purple;T $s 72 450 820 28 '设计思路：前端负责体验和展示，后端负责安全调度与第三方能力调用，统一返回 type 字段驱动页面组件切换。' 13 $white 1 2|Out-Null
# 6
$s=$prs.Slides.Add(6,$blank);Title $s '工作亮点' '从“能聊天”升级为“能听、能说、能执行任务”的 AI 应用' 6;$hs=@(@('01 多轮对话能力','支持连续追问：先问承德美食，再追问这些在哪能吃到。'),@('02 AI 多能力集成','对话、文生图、翻译、天气、音乐和桌面应用统一入口。'),@('03 语音助手体验','支持语音识别、唤醒词“小文小文”和回复朗读。'),@('04 异步文生图体验','任务提交后进入生成中状态，通过轮询展示结果。'),@('05 安全桌面控制','白名单机制打开本机应用，兼顾可用性与安全性。'),@('06 组件化可扩展','前端组件和 Hook 拆分，后端统一指令路由。'));for($i=0;$i -lt 6;$i++){Card $s (58+($i%2)*440) (118+[math]::Floor($i/2)*112) 405 86 $hs[$i][0] $hs[$i][1] $acc[$i]}
# 7
$s=$prs.Slides.Add(7,$blank);Title $s '问题与改进' '当前版本已能演示核心能力，但仍需要从稳定性、智能化和工程化继续提升' 7;$rs=@(@('意图识别','关键词规则为主','引入大模型意图分类，减少误判'),@('音乐播放','受版权和外链限制','增加多结果选择、合法音乐源和失败重试'),@('语音能力','依赖浏览器支持','增加纠错、自动朗读和语速音调调节'),@('后端结构','功能集中在 app.py','拆分 services、utils、config 模块'),@('部署形态','本地开发模式','关闭 debug，增加生产配置和日志监控'));for($i=0;$i -lt 5;$i++){Card $s 62 (128+$i*62) 170 42 $rs[$i][0] '' $acc[$i];T $s 270 (136+$i*62) 230 22 $rs[$i][1] 10 $muted 0 1|Out-Null;T $s 545 (136+$i*62) 350 22 $rs[$i][2] 10 $muted 0 1|Out-Null}
# 8
$s=$prs.Slides.Add(8,$blank);Title $s '下季度计划' '围绕“更智能、更稳定、更可展示、更可扩展”推进下一阶段迭代' 8;$ps=@(@('第 1 阶段 体验增强',"完善多轮记忆`n自动朗读开关`n优化默认示例`n增强错误提示"),@('第 2 阶段 能力扩展',"日程 / 备忘录`n图片历史与下载`n音乐收藏`n联网搜索入口"),@('第 3 阶段 工程优化',"后端服务模块化`n统一响应结构`n日志和错误码`n生产环境配置"),@('第 4 阶段 部署展示',"Docker 或云部署`nHTTPS / Nginx`n演示脚本`n完善答辩材料"));for($i=0;$i -lt 4;$i++){Card $s (58+$i*220) 142 190 260 $ps[$i][0] $ps[$i][1] $acc[$i]};T $s 72 450 820 28 '目标：从“本地可运行的 AI 助手原型”升级为“可持续迭代、可部署展示的智能应用平台”。' 14 $white 1 2|Out-Null
# 9
$s=$prs.Slides.Add(9,$blank);Title $s '建议演示路径' '用一条完整用户路径展示小文智能 APP 的能力闭环' 9;$ds=@(@('1. 语音唤醒','说“小文小文”，进入指令识别'),@('2. 生活查询','询问“承德天气怎么样”'),@('3. 连续对话','先问承德美食，再追问位置'),@('4. 音乐播放','说“播放稻香”，展示播放器'),@('5. AI 创作','说“画一只水彩小猫”'),@('6. 桌面控制','说“打开计算器”'));for($i=0;$i -lt 6;$i++){Card $s (68+($i%3)*290) (130+[math]::Floor($i/3)*145) 250 96 $ds[$i][0] $ds[$i][1] $acc[$i]};T $s 72 450 820 28 '演示重点：让观众看到小文不是静态页面，而是可以理解指令、调用能力并完成任务的 AI 应用。' 13 $white 1 2|Out-Null
# 10
$s=$prs.Slides.Add(10,$blank);Bg $s;T $s 65 120 830 60 '感谢聆听' 40 $white 1 2|Out-Null;T $s 110 200 740 40 '小文智能 APP 将继续向更自然、更稳定、更具执行力的个人 AI 助手演进' 16 $muted 0 2|Out-Null;Chip $s 180 270 '能听' $cyan;Chip $s 315 270 '能说' $blue;Chip $s 450 270 '能聊' $purple;Chip $s 585 270 '能画' $pink;Chip $s 720 270 '能开' $green;T $s 350 370 260 40 'Q&A' 28 $cyan 1 2|Out-Null;Footer $s 10
$prs.SaveAs($out)
$prs.Close()
$pp.Quit()
Write-Output $out
