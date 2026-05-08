$out='D:\Desktop\xiaowen\xiaowen_ai_app_optimized.pptx'
$pp=New-Object -ComObject PowerPoint.Application
$pp.Visible=-1
$prs=$pp.Presentations.Add()
$prs.PageSetup.SlideWidth=960
$prs.PageSetup.SlideHeight=540
$blank=12
function RGB($r,$g,$b){ $r + $g*256 + $b*65536 }
$bg=RGB 8 12 28; $panel=RGB 22 32 64; $panel2=RGB 31 44 86
$white=RGB 246 248 255; $muted=RGB 178 192 225
$cyan=RGB 58 220 255; $blue=RGB 72 142 255; $purple=RGB 155 92 255; $green=RGB 76 230 170; $orange=RGB 255 180 90; $pink=RGB 255 92 180
$acc=@($cyan,$blue,$purple,$green,$orange,$pink)
function TextBox($s,$x,$y,$w,$h,$text,$size,$color,$bold,$align){
  if($h -lt 12){$h=12}; if($w -lt 20){$w=20}
  $o=$s.Shapes.AddTextbox(1,[float]$x,[float]$y,[float]$w,[float]$h)
  $o.TextFrame.WordWrap=-1
  $r=$o.TextFrame.TextRange
  $r.Text=[string]$text
  $r.Font.Name='Microsoft YaHei'
  $r.Font.Size=[float]$size
  $r.Font.Color.RGB=[int]$color
  $r.Font.Bold=[int]$bold
  $r.ParagraphFormat.Alignment=[int]$align
  return $o
}
function Bg($s){
  $r=$s.Shapes.AddShape(1,0,0,960,540);$r.Fill.ForeColor.RGB=$bg;$r.Line.Visible=0
  $o=$s.Shapes.AddShape(9,735,-60,250,250);$o.Fill.ForeColor.RGB=$purple;$o.Fill.Transparency=.55;$o.Line.Visible=0
  $o=$s.Shapes.AddShape(9,-65,375,210,210);$o.Fill.ForeColor.RGB=$blue;$o.Fill.Transparency=.67;$o.Line.Visible=0
  $o=$s.Shapes.AddShape(9,410,86,90,90);$o.Fill.ForeColor.RGB=$cyan;$o.Fill.Transparency=.82;$o.Line.Visible=0
}
function Footer($s,$n){
  [void](TextBox $s 42 506 430 20 '小文智能 APP · AI 项目汇报' 8 (RGB 130 150 195) 0 1)
  [void](TextBox $s 884 504 40 20 ([string]::Format('{0:d2}',$n)) 9 $cyan -1 3)
}
function Title($s,$t,$sub,$n){
  Bg $s
  [void](TextBox $s 55 30 760 38 $t 24 $white -1 1)
  [void](TextBox $s 57 73 760 24 $sub 10 $muted 0 1)
  $a=$s.Shapes.AddShape(1,57,106,92,4);$a.Fill.ForeColor.RGB=$cyan;$a.Line.Visible=0
  Footer $s $n
}
function Card($s,$x,$y,$w,$h,$head,$body,$color){
  $c=$s.Shapes.AddShape(5,[float]$x,[float]$y,[float]$w,[float]$h);$c.Fill.ForeColor.RGB=$panel;$c.Fill.Transparency=.03;$c.Line.ForeColor.RGB=RGB 70 92 150
  $bar=$s.Shapes.AddShape(1,[float]$x,[float]$y,6,[float]$h);$bar.Fill.ForeColor.RGB=$color;$bar.Line.Visible=0
  [void](TextBox $s ($x+16) ($y+10) ($w-30) 23 $head 11.5 $white -1 1)
  if([string]$body -ne ''){[void](TextBox $s ($x+16) ($y+42) ($w-28) ($h-48) $body 9.3 $muted 0 1)}
}
function Pill($s,$x,$y,$text,$color){
  $p=$s.Shapes.AddShape(5,[float]$x,[float]$y,120,28);$p.Fill.ForeColor.RGB=$color;$p.Fill.Transparency=.15;$p.Line.ForeColor.RGB=$color
  [void](TextBox $s ($x+4) ($y+6) 112 16 $text 8.5 $white -1 2)
}
function Metric($s,$x,$y,$num,$lab,$color){
  $m=$s.Shapes.AddShape(5,[float]$x,[float]$y,170,74);$m.Fill.ForeColor.RGB=$panel2;$m.Line.ForeColor.RGB=$color
  [void](TextBox $s ($x+8) ($y+8) 154 28 $num 20 $color -1 2)
  [void](TextBox $s ($x+8) ($y+45) 154 18 $lab 8.3 $muted 0 2)
}
# 1 cover
$s=$prs.Slides.Add(1,$blank);Bg $s
[void](TextBox $s 58 72 620 28 'AI VOICE ASSISTANT · PRODUCT REPORT' 11 $cyan -1 1)
[void](TextBox $s 56 112 620 58 '小文智能 APP 项目汇报' 34 $white -1 1)
[void](TextBox $s 60 188 575 48 '以自然语言和语音交互为入口，集成 AI 对话、文生图、天气、音乐、翻译与桌面控制的智能助手原型。' 14 $muted 0 1)
Pill $s 62 260 'React + Vite' $blue; Pill $s 198 260 'Flask API' $green; Pill $s 334 260 'DashScope' $purple; Pill $s 470 260 'Web Speech' $cyan
[void](TextBox $s 60 452 330 20 '汇报人：刘汉文    2026' 10 (RGB 150 166 210) 0 1); Footer $s 1
# 2 toc
$s=$prs.Slides.Add(2,$blank);Title $s '目录' '按“目标—方法—成果—复盘—计划”组织汇报内容' 2
$items=@('项目目标与应用场景','应用方式、方法与核心数据','系统架构与技术实现','工作亮点与项目价值','问题复盘与改进方向','下季度计划与结尾感谢')
for($i=0;$i -lt 6;$i++){[void](TextBox $s 85 (128+$i*56) 50 22 ([string]::Format('{0:d2}',$i+1)) 13 $cyan -1 2);[void](TextBox $s 155 (128+$i*56) 620 22 $items[$i] 15 $white -1 1)}
# 3 goals
$s=$prs.Slides.Add(3,$blank);Title $s '项目目标与应用场景' '目标不是做一个单纯聊天框，而是做一个能理解指令并执行任务的 AI 应用入口' 3
Card $s 60 130 260 110 '初始目标' "自然语言交互`n语音识别与唤醒`nAI 问答与创作`n常用工具一键调用" $cyan
Card $s 350 130 260 110 '用户场景' "查天气、听音乐`n问美食、讲故事`n生成图片、划词翻译`n打开本机应用" $purple
Card $s 640 130 260 110 '项目定位' "个人桌面 AI 助手`n智能音箱 Web 原型`nAI 多功能工作台雏形`n课程设计展示项目" $green
[void](TextBox $s 90 305 780 36 '一句话总结：小文智能 APP 将“AI 能力”包装成用户可以直接使用的生活与桌面助手。' 18 $white -1 2)
Card $s 92 372 180 70 '能听' '语音识别 / 唤醒词' $cyan;Card $s 292 372 180 70 '能聊' '多轮 AI 对话' $purple;Card $s 492 372 180 70 '能做' '调用服务与工具' $green;Card $s 692 372 180 70 '能展示' '卡片反馈与日志' $orange
# 4 methods
$s=$prs.Slides.Add(4,$blank);Title $s '应用方式、方法与核心数据' '通过统一指令入口，把用户输入转换为可执行的功能调用' 4
Card $s 60 126 190 88 '1 输入' '文字 / 语音 / 示例按钮' $cyan;Card $s 280 126 190 88 '2 识别' '意图判断 / 模式路由' $blue;Card $s 500 126 190 88 '3 调用' 'AI / 天气 / 音乐 / 图片 / 应用' $purple;Card $s 720 126 190 88 '4 展示' '卡片 / 朗读 / 日志' $green
Metric $s 80 268 '12+' '核心功能点' $cyan;Metric $s 285 268 '3' '核心后端接口' $green;Metric $s 490 268 '10+' '前端组件模块' $purple;Metric $s 695 268 '12' '上下文消息保留' $orange
Card $s 90 390 245 74 '前端' 'React + Vite + 组件化 + localStorage' $blue;Card $s 358 390 245 74 '后端' 'Flask + 统一 API + 第三方服务编排' $green;Card $s 626 390 245 74 'AI' 'DashScope 对话模型 + 文生图任务' $purple
# 5 architecture
$s=$prs.Slides.Add(5,$blank);Title $s '系统架构与技术实现' '前端负责体验，后端负责调度，外部服务提供 AI 与生活能力' 5
Card $s 55 130 190 270 '用户交互层' "文字输入`n语音识别`n唤醒词`n示例指令`n划词工具" $cyan
Card $s 278 130 190 270 '前端展示层' "ChatPanel`nWeatherCard`nMusicPlayer`nImagePreview`nLogPanel" $blue
Card $s 501 130 190 270 '后端调度层' "Flask API`nparse_command`n上下文管理`n白名单启动`n错误兜底" $green
Card $s 724 130 190 270 '外部能力层' "DashScope`n高德天气`n网易云接口`nWindows 应用`n浏览器语音" $purple
[void](TextBox $s 80 448 800 30 '统一返回 type 字段，由前端根据 type 切换聊天、天气、音乐、图片等展示组件。' 13 $white -1 2)
# 6 highlights
$s=$prs.Slides.Add(6,$blank);Title $s '工作亮点与项目价值' '围绕 AI 应用可用性，完成了从“能回复”到“能执行”的能力升级' 6
$hs=@(@('多轮对话','能理解“这些美食在哪能吃到”这类连续追问。'),@('语音体验','支持语音识别、唤醒词和回复朗读。'),@('AI 创作','对话与文生图打通，支持文字生成图片。'),@('异步反馈','图片生成采用任务轮询，减少等待焦虑。'),@('桌面控制','白名单方式打开本机应用，安全可控。'),@('可扩展架构','组件化前端 + 统一后端路由，便于新增能力。'))
for($i=0;$i -lt 6;$i++){Card $s (60+($i%2)*430) (126+[math]::Floor($i/2)*105) 390 78 $hs[$i][0] $hs[$i][1] $acc[$i]}
# 7 problems
$s=$prs.Slides.Add(7,$blank);Title $s '问题复盘与改进方向' '当前版本可演示核心能力，下一步重点提升稳定性、智能化和工程化水平' 7
$rows=@(@('意图识别','规则判断为主','引入大模型意图分类'),@('音乐播放','受版权和外链限制','增加合法音乐源与失败重试'),@('语音能力','依赖浏览器支持','加入纠错、语速和自动朗读配置'),@('后端结构','逻辑集中在 app.py','拆分 services / utils / config'),@('部署形态','本地开发模式','增加生产配置、日志和部署脚本'))
for($i=0;$i -lt 5;$i++){Card $s 65 (128+$i*62) 160 42 $rows[$i][0] '' $acc[$i];[void](TextBox $s 270 (136+$i*62) 240 20 $rows[$i][1] 10 $muted 0 1);[void](TextBox $s 560 (136+$i*62) 310 20 $rows[$i][2] 10 $white -1 1)}
# 8 plan
$s=$prs.Slides.Add(8,$blank);Title $s '下季度计划' '围绕“更智能、更稳定、更可展示、更可扩展”推进迭代' 8
$ps=@(@('体验增强',"完善长期记忆`n自动朗读开关`n优化默认指令`n增强错误提示"),@('能力扩展',"日程 / 备忘录`n图片历史与下载`n音乐收藏`n联网搜索入口"),@('工程优化',"后端模块化`n统一响应结构`n日志和错误码`n生产环境配置"),@('部署展示',"Docker 或云部署`nNginx / HTTPS`n演示脚本`n答辩材料完善"))
for($i=0;$i -lt 4;$i++){Card $s (62+$i*218) 142 188 250 $ps[$i][0] $ps[$i][1] $acc[$i]}
[void](TextBox $s 90 446 780 30 '阶段目标：从本地 AI 助手原型，升级为可持续迭代、可部署展示的智能应用平台。' 14 $white -1 2)
# 9 demo
$s=$prs.Slides.Add(9,$blank);Title $s '建议现场演示路径' '用一条完整用户路径展示小文智能 APP 的能力闭环' 9
$ds=@(@('语音唤醒','“小文小文”'),@('生活查询','承德天气怎么样'),@('连续对话','承德美食 → 这些在哪吃'),@('音乐播放','播放稻香'),@('AI 创作','画一只水彩小猫'),@('桌面控制','打开计算器'))
for($i=0;$i -lt 6;$i++){Card $s (68+($i%3)*286) (136+[math]::Floor($i/3)*130) 245 88 $ds[$i][0] $ds[$i][1] $acc[$i]}
[void](TextBox $s 85 446 790 32 '演示重点：让观众看到小文可以理解指令、调用能力、展示结果，而不只是聊天。' 14 $white -1 2)
# 10 thanks
$s=$prs.Slides.Add(10,$blank);Bg $s
[void](TextBox $s 80 125 800 58 '感谢聆听' 40 $white -1 2)
[void](TextBox $s 120 205 720 36 '小文智能 APP 将继续向更自然、更稳定、更具执行力的个人 AI 助手演进' 16 $muted 0 2)
Pill $s 190 282 '能听' $cyan;Pill $s 325 282 '能说' $blue;Pill $s 460 282 '能聊' $purple;Pill $s 595 282 '能画' $pink;Pill $s 730 282 '能开' $green
[void](TextBox $s 350 382 260 40 'Q&A' 28 $cyan -1 2);Footer $s 10
$prs.SaveAs($out)
$prs.Close()
$pp.Quit()
Write-Output $out
