$src='D:\Desktop\xiaowen\xiaowen_ai_app_optimized.pptx'
$out='D:\Desktop\xiaowen\小文智能APP项目汇报-最终增强版.pptx'
$pp=New-Object -ComObject PowerPoint.Application
$pp.Visible=-1
$prs=$pp.Presentations.Open($src,$false,$false,$true)
function RGB($r,$g,$b){ $r + $g*256 + $b*65536 }
$cyan=RGB 58 220 255; $blue=RGB 72 142 255; $purple=RGB 155 92 255; $green=RGB 76 230 170; $orange=RGB 255 180 90; $pink=RGB 255 92 180; $white=RGB 246 248 255; $muted=RGB 178 192 225; $panel=RGB 22 32 64
function TextBox($s,$x,$y,$w,$h,$text,$size,$color,$bold,$align){
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
function SoftCircle($s,$x,$y,$size,$color,$trans,$lineTrans){
  $o=$s.Shapes.AddShape(9,[float]$x,[float]$y,[float]$size,[float]$size)
  $o.Fill.Visible=0
  $o.Line.ForeColor.RGB=$color
  $o.Line.Transparency=$lineTrans
  $o.Line.Weight=2
  return $o
}
function SolidCircle($s,$x,$y,$size,$color,$trans){
  $o=$s.Shapes.AddShape(9,[float]$x,[float]$y,[float]$size,[float]$size)
  $o.Fill.ForeColor.RGB=$color
  $o.Fill.Transparency=$trans
  $o.Line.Visible=0
  return $o
}
function Panel($s,$x,$y,$w,$h,$text,$color){
  $p=$s.Shapes.AddShape(5,[float]$x,[float]$y,[float]$w,[float]$h)
  $p.Fill.ForeColor.RGB=$color
  $p.Fill.Transparency=.18
  $p.Line.ForeColor.RGB=$color
  [void](TextBox $s ($x+6) ($y+6) ($w-12) 18 $text 8.5 $white -1 2)
}
# enhance cover
$s=$prs.Slides.Item(1)
[void](SoftCircle $s 705 110 185 $cyan .8 .2)
[void](SoftCircle $s 680 85 235 $purple .8 .35)
[void](SoftCircle $s 730 135 135 $blue .8 .15)
[void](SolidCircle $s 772 176 50 $cyan .12)
[void](TextBox $s 763 190 68 18 'AI' 15 $white -1 2)
Panel $s 670 330 86 30 '智能问答' $cyan
Panel $s 770 330 86 30 '语音交互' $blue
Panel $s 670 372 86 30 '文生图' $purple
Panel $s 770 372 86 30 '桌面控制' $green
Panel $s 720 414 86 30 '多轮记忆' $orange
[void](TextBox $s 60 316 560 24 '项目关键词：自然语言入口 · 多服务编排 · 语音助手体验 · 可扩展 AI 工作台' 11 $white -1 1)
# add capability matrix slide after methods
$blank=12
$new=$prs.Slides.Add(5,$blank)
# background
$r=$new.Shapes.AddShape(1,0,0,960,540);$r.Fill.ForeColor.RGB=RGB 8 12 28;$r.Line.Visible=0
$o=$new.Shapes.AddShape(9,735,-60,250,250);$o.Fill.ForeColor.RGB=$purple;$o.Fill.Transparency=.55;$o.Line.Visible=0
$o=$new.Shapes.AddShape(9,-65,375,210,210);$o.Fill.ForeColor.RGB=$blue;$o.Fill.Transparency=.67;$o.Line.Visible=0
[void](TextBox $new 55 30 760 38 '核心能力矩阵' 24 $white -1 1)
[void](TextBox $new 57 73 760 24 '从输入、理解、服务调用到结果表达，形成完整 AI 应用闭环' 10 $muted 0 1)
$a=$new.Shapes.AddShape(1,57,106,92,4);$a.Fill.ForeColor.RGB=$cyan;$a.Line.Visible=0
$items=@(
  @('输入层','文字输入 / 语音识别 / 唤醒词',$cyan),
  @('理解层','意图识别 / 多轮上下文 / 模式判断',$blue),
  @('能力层','对话 / 天气 / 音乐 / 文生图 / 翻译 / 应用启动',$purple),
  @('反馈层','卡片展示 / 播放器 / 图片预览 / 日志 / 朗读',$green),
  @('安全层','API Key 后端托管 / 应用白名单 / 异常兜底',$orange),
  @('扩展层','模块化服务 / 可接入日程、搜索、知识库',$pink)
)
for($i=0;$i -lt 6;$i++){
  $x=72+($i%3)*286; $y=140+[math]::Floor($i/3)*145
  $card=$new.Shapes.AddShape(5,[float]$x,[float]$y,245,98);$card.Fill.ForeColor.RGB=$panel;$card.Fill.Transparency=.03;$card.Line.ForeColor.RGB=$items[$i][2]
  $bar=$new.Shapes.AddShape(1,[float]$x,[float]$y,6,98);$bar.Fill.ForeColor.RGB=$items[$i][2];$bar.Line.Visible=0
  [void](TextBox $new ($x+18) ($y+14) 210 22 $items[$i][0] 12 $white -1 1)
  [void](TextBox $new ($x+18) ($y+46) 205 34 $items[$i][1] 9.5 $muted 0 1)
}
[void](TextBox $new 42 506 430 20 '小文智能 APP · AI 项目汇报' 8 (RGB 130 150 195) 0 1)
[void](TextBox $new 884 504 40 20 '05' 9 $cyan -1 3)
# architecture slide is now 6: add arrows between columns
$s=$prs.Slides.Item(6)
for($i=0;$i -lt 3;$i++){
  $x=250+$i*223
  $arr=$s.Shapes.AddShape(33,[float]$x,250,42,28)
  $arr.Fill.ForeColor.RGB=$cyan
  $arr.Fill.Transparency=.08
  $arr.Line.Visible=0
}
[void](TextBox $s 385 414 190 22 '统一指令入口 /api/send-task' 10 $cyan -1 2)
# highlight slide now 7: add conclusion ribbon
$s=$prs.Slides.Item(7)
$rib=$s.Shapes.AddShape(5,90,452,780,34);$rib.Fill.ForeColor.RGB=$purple;$rib.Fill.Transparency=.18;$rib.Line.ForeColor.RGB=$purple
[void](TextBox $s 110 460 740 18 '项目亮点归纳：用统一入口把 AI 能力、语音交互和桌面控制组合成可演示的智能应用。' 10 $white -1 2)
# update slide numbers manually for later inserted slide
for($idx=6;$idx -le $prs.Slides.Count;$idx++){
  # leave existing footers; add small corrected number at top right
  [void](TextBox $prs.Slides.Item($idx) 900 28 32 16 ([string]::Format('{0:d2}',$idx)) 8 $cyan -1 3)
}
$prs.SaveAs($out)
$prs.Close()
$pp.Quit()
Write-Output $out
