from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# 注册中文字体（需提前下载SimSun.ttf）
pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))

# 创建PDF文档
doc = SimpleDocTemplate("report.pdf", pagesize=A4)
styles = getSampleStyleSheet()
content = []

# 添加标题
title = Paragraph("<font name='SimSun' size=18>2023年销售分析报告</font>", styles['Heading1'])
content.append(title)
content.append(Spacer(1, 20))  # 添加间距

# 插入饼图
img = Image('sales_pie.png', width=400, height=300)
content.append(img)
content.append(Spacer(1, 20))

# 添加分析文本
text = Paragraph("<font name='SimSun'>结论：品类A占比最高（25%），需重点关注库存...</font>", styles['Normal'])
content.append(text)

# 生成PDF
doc.build(content)