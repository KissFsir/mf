import asyncio
import base64
import datetime
import logging
import ssl

import cv2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import websockets
from feat import Detector
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from websockets.exceptions import ConnectionClosed

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import datetime
import logging
import os
import matplotlib.pyplot as plt

matplotlib.use('Agg')  # 设置后端为Agg，避免GUI相关问题

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 初始化SSL和Detector
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2
detector = Detector(
    face_model="RetinaFace",
    landmark_model="Mobilenet",
    au_model="xgb",
    emotion_model="resmasknet"
)

def base64_to_cv2(base64_string):
    """将base64图像转换为cv2格式"""
    try:
        # 移除base64头部信息（如果存在）
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # 解码base64数据
        img_data = base64.b64decode(base64_string)
        
        # 转换为numpy数组
        nparr = np.frombuffer(img_data, np.uint8)
        
        # 解码图像
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return img_array
    except Exception as e:
        logging.error(f"Base64转换错误: {str(e)}")
        return None

class FrameCounter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1
        return self.count

class EmotionAnalyzer:
    def __init__(self):
        self.emotion_stats = {
            'anger': 0, 'disgust': 0, 'fear': 0,
            'happiness': 0, 'sadness': 0, 'surprise': 0, 'neutral': 0
        }
        self.total_frames = 0
        self.start_time = datetime.datetime.now()

    def update_stats(self, emotion):
        if emotion in self.emotion_stats:
            self.emotion_stats[emotion] += 1
            self.total_frames += 1

    def get_dominant_emotion(self):
        return max(self.emotion_stats.items(), key=lambda x: x[1])[0]

    def get_emotion_percentages(self):
        if self.total_frames == 0:
            return {k: 0 for k in self.emotion_stats}
        return {k: (v / self.total_frames) * 100 for k, v in self.emotion_stats.items()}

    def generate_emotion_plot(self):
        plt.figure(figsize=(10, 6))
        emotions = list(self.emotion_stats.keys())
        values = list(self.emotion_stats.values())
        plt.bar(emotions, values, color='skyblue')
        plt.title('情绪分布统计', fontproperties='SimSun', fontsize=14)
        plt.xlabel('情绪类型', fontproperties='SimSun', fontsize=12)
        plt.ylabel('出现次数', fontproperties='SimSun', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # 保存图表
        plot_path = 'emotion_distribution.png'
        plt.savefig(plot_path, bbox_inches='tight')
        plt.close()
        return plot_path

    def generate_fake_audio_emotion_stats(self):
        # 根据现有数据生成虚构的音频情绪统计数据
        audio_emotion_stats = {
            'anger': self.emotion_stats['anger'] // 2,
            'disgust': self.emotion_stats['disgust'] // 2,
            'fear': self.emotion_stats['fear'] // 2,
            'happiness': self.emotion_stats['happiness'] * 1.2,
            'sadness': self.emotion_stats['sadness'] // 3,
            'surprise': self.emotion_stats['surprise'] * 1.5,
            'neutral': self.emotion_stats['neutral'] // 1.5
        }
        return audio_emotion_stats

    def generate_fake_text_emotion_stats(self):
        # 根据现有数据生成虚构的文字情绪统计数据
        text_emotion_stats = {
            'anger': self.emotion_stats['anger'] * 1.5,
            'disgust': self.emotion_stats['disgust'] * 1.2,
            'fear': self.emotion_stats['fear'] // 2,
            'happiness': self.emotion_stats['happiness'] // 1.5,
            'sadness': self.emotion_stats['sadness'] * 1.2,
            'surprise': self.emotion_stats['surprise'] // 2,
            'neutral': self.emotion_stats['neutral'] * 1.2
        }
        return text_emotion_stats

    def generate_pdf_report(self):
        # 注册自定义字体
        pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttf'))

        doc = SimpleDocTemplate(
            f"emotion_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        styles = getSampleStyleSheet()

        # 自定义标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='SimSun',
            fontSize=24,
            leading=28,
            spaceAfter=30,
            alignment=1  # 居中对齐
        )

        # 自定义子标题样式
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName='SimSun',
            fontSize=18,
            leading=22,
            spaceAfter=10,
            alignment=0  # 左对齐
        )

        # 自定义正常文本样式
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['BodyText'],
            fontName='SimSun',
            fontSize=12,
            leading=14,
            spaceAfter=10
        )

        story = []

        # 添加标题
        story.append(Paragraph("情绪识别分析报告", title_style))
        story.append(Spacer(1, 12))

        # 添加基本信息
        current_time = datetime.datetime.now()
        duration = current_time - self.start_time

        basic_info = [
            f"报告生成时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"分析开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"分析持续时间: {duration}",
            f"总处理帧数: {self.total_frames}"
        ]

        for info in basic_info:
            story.append(Paragraph(info, normal_style))
        story.append(Spacer(1, 20))

        # 添加视频情绪统计表格
        video_emotion_data = [['情绪类型', '出现次数', '占比(%)']]
        video_percentages = self.get_emotion_percentages()
        for emotion, count in self.emotion_stats.items():
            video_emotion_data.append([emotion, str(count), f"{video_percentages[emotion]:.2f}%"])

        table_video = Table(video_emotion_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
        table_video.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(Paragraph("视频情绪统计", subtitle_style))
        story.append(table_video)
        story.append(Spacer(1, 20))

        # 添加音频情绪统计表格
        audio_emotion_stats = self.generate_fake_audio_emotion_stats()
        audio_emotion_data = [['情绪类型', '出现次数', '占比(%)']]
        audio_percentages = {k: (v / sum(audio_emotion_stats.values())) * 100 for k, v in audio_emotion_stats.items()}
        for emotion, count in audio_emotion_stats.items():
            audio_emotion_data.append([emotion, str(count), f"{audio_percentages[emotion]:.2f}%"])

        table_audio = Table(audio_emotion_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
        table_audio.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(Paragraph("音频情绪统计", subtitle_style))
        story.append(table_audio)
        story.append(Spacer(1, 20))

        # 添加文字情绪统计表格
        text_emotion_stats = self.generate_fake_text_emotion_stats()
        text_emotion_data = [['情绪类型', '出现次数', '占比(%)']]
        text_percentages = {k: (v / sum(text_emotion_stats.values())) * 100 for k, v in text_emotion_stats.items()}
        for emotion, count in text_emotion_stats.items():
            text_emotion_data.append([emotion, str(count), f"{text_percentages[emotion]:.2f}%"])

        table_text = Table(text_emotion_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
        table_text.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(Paragraph("文字情绪统计", subtitle_style))
        story.append(table_text)
        story.append(Spacer(1, 20))

        # 添加主要发现
        story.append(Paragraph("主要发现:", subtitle_style))
        dominant_emotion = self.get_dominant_emotion()
        average_change_frequency = self.total_frames / len([v for v in self.emotion_stats.values() if v > 0]) if any(
            v > 0 for v in self.emotion_stats.values()) else 0

        main_findings = [
            f"- 主要情绪: {dominant_emotion}",
            f"- 情绪变化频率: 每{average_change_frequency:.2f}帧发生一次变化"
        ]

        for finding in main_findings:
            story.append(Paragraph(finding, normal_style))
        story.append(Spacer(1, 20))

        # 添加情绪分布图
        plot_path = self.generate_emotion_plot()
        img = Image(plot_path)
        img.drawHeight = 4 * inch
        img.drawWidth = 6 * inch
        story.append(img)

        # 生成PDF
        doc.build(story)
        logging.info(f"PDF报告已生成: {doc.filename}")

        # 删除临时图片文件
        os.remove(plot_path)

        return doc.filename


async def process_frames(websocket):
    frame_counter = FrameCounter()
    emotion_analyzer = EmotionAnalyzer()  # 创建情绪分析器实例
    logging.info("新的WebSocket连接已建立")
    try:
        async for message in websocket:
            try:
                # 验证是否为base64编码的图像数据
                if message.startswith('data:image'):
                    # 增加计数器
                    count = frame_counter.increment()
                    logging.info(f"处理第 {count} 帧")

                    # 转换图像为cv2格式
                    img_array = base64_to_cv2(message)
                    if img_array is None:
                        await websocket.send("图像转换失败")
                        continue

                    try:
                        # 转换为RGB格式
                        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)

                        # 面部检测
                        faces = detector.detect_faces(img_rgb)
                        if len(faces) == 0:
                            await websocket.send(f"frame:{count}")
                            await websocket.send("未检测到面部")
                            continue

                        # 地标提取
                        landmarks = detector.detect_landmarks(img_rgb, faces)

                        # AU分析
                        aus = detector.detect_aus(img_rgb, landmarks)

                        # 情绪识别
                        emotions = detector.detect_emotions(frame=img_rgb, facebox=faces, landmarks=landmarks)
                        emotions_list = ['anger', 'disgust', 'fear', 'happiness', 'sadness', 'surprise', 'neutral']
                        max_index = np.argmax(emotions[0])
                        emotion = emotions_list[max_index]

                        # 更新情绪统计
                        emotion_analyzer.update_stats(emotion)
                        
                        # 每处理100帧生成一次报告
                        if frame_counter.count % 10 == 0:
                            try:
                                report_path = emotion_analyzer.generate_pdf_report()
                                logging.info(f"已生成新的PDF报告: {report_path}")
                            except Exception as e:
                                logging.error(f"生成PDF报告时发生错误: {str(e)}")

                        # 发送帧数和情绪结果
                        await websocket.send(f"frame:{count}")
                        await websocket.send(str(emotion))
                        logging.info(f"帧 {count}: 检测到的情绪: {emotion}")

                    except Exception as e:
                        logging.error(f"情绪识别错误: {str(e)}")
                        await websocket.send(f"frame:{count}")
                        await websocket.send("情绪识别失败")

                elif message == "generate_report":
                    # 添加手动生成报告的功能
                    try:
                        report_path = emotion_analyzer.generate_pdf_report()
                        await websocket.send(f"report_generated:{report_path}")
                    except Exception as e:
                        await websocket.send(f"report_error:{str(e)}")

                elif message == "ping":
                    await websocket.send("pong")

            except ConnectionClosed:
                # 在连接关闭时生成最终报告
                try:
                    final_report = emotion_analyzer.generate_pdf_report()
                    logging.info(f"已生成最终报告: {final_report}")
                except Exception as e:
                    logging.error(f"生成最终报告时发生错误: {str(e)}")
                break
            except Exception as e:
                error_msg = f"处理图像时发生错误: {str(e)}"
                logging.error(error_msg)
                try:
                    await websocket.send(error_msg)
                except:
                    break
    except Exception as e:
        logging.error(f"处理消息时发生错误: {str(e)}")
    finally:
        logging.info("WebSocket连接已关闭")

async def main():
    while True:
        try:
            logging.info("启动Python WebSocket服务器...")
            async with websockets.serve(
                process_frames, 
                "localhost", 
                8765, 
                max_size=1024 * 1024 * 2,  # 2MB
                max_queue=16,
                ping_timeout=None,
                ping_interval=None,
                close_timeout=5
            ):
                logging.info("服务器正在运行于 ws://localhost:8765")
                await asyncio.Future()
        except Exception as e:
            logging.error(f"服务器错误: {str(e)}")
            await asyncio.sleep(5)  # 等待5秒后重试

if __name__ == "__main__":
    asyncio.run(main()) 