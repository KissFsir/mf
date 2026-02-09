"""
PyFeat 检测器测试脚本 - 修复版本
"""

import os
import cv2
import numpy as np
import shutil
from feat import Detector
from feat.utils import FEAT_EMOTION_COLUMNS

def cleanup_model_directory(model_dir):
    """清理模型目录，删除可能损坏的文件"""
    print("清理模型目录...")
    if os.path.exists(model_dir):
        # 删除整个模型目录
        shutil.rmtree(model_dir)
        print(f"已删除目录: {model_dir}")

    # 重新创建目录
    os.makedirs(model_dir, exist_ok=True)
    print(f"已重新创建目录: {model_dir}")

    return model_dir

def setup_environment():
    """设置环境，包括模型下载路径"""
    # 设置模型下载路径
    model_dir = os.path.join(os.path.dirname(__file__), "models")

    # 清理并重新创建目录
    model_dir = cleanup_model_directory(model_dir)
    os.environ['FIT_CACHE_DIR'] = model_dir
    print(f"模型将下载到: {model_dir}")

    return model_dir

def initialize_detector(max_retries=3):
    """初始化 PyFeat 检测器，带有重试机制"""
    for attempt in range(max_retries):
        print(f"尝试初始化检测器 (尝试 {attempt + 1}/{max_retries})...")

        try:
            # 使用您指定的配置初始化检测器
            detector = Detector(
                face_model="RetinaFace",
                landmark_model="Mobilenet",
                au_model="xgb",
                emotion_model="resmasknet"
            )

            print("✓ 检测器初始化成功!")
            print("配置详情:")
            print(f"  人脸检测模型: {detector.face_model}")
            print(f"  关键点检测模型: {detector.landmark_model}")
            print(f"  AU检测模型: {detector.au_model}")
            print(f"  情绪检测模型: {detector.emotion_model}")

            return detector

        except Exception as e:
            print(f"✗ 检测器初始化失败: {e}")

            # 如果是最后一次尝试，不再重试
            if attempt == max_retries - 1:
                print("已达到最大重试次数，无法初始化检测器")
                return None

            # 等待一段时间后重试
            import time
            wait_time = 5 * (attempt + 1)  # 等待时间递增
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

            # 清理模型目录并重试
            model_dir = os.path.join(os.path.dirname(__file__), "models")
            cleanup_model_directory(model_dir)

def test_with_sample_image(detector, image_path=None):
    """使用样本图像测试检测器"""
    print("\n开始测试检测器...")

    # 如果没有提供图像路径，创建一个简单的测试图像
    if image_path is None or not os.path.exists(image_path):
        print("创建测试图像...")
        # 创建一个简单的测试图像（黑色背景上的白色矩形模拟人脸）
        test_image = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (50, 50), (150, 150), (255, 255, 255), -1)
        image_path = "test_image.jpg"
        cv2.imwrite(image_path, test_image)
        print(f"创建测试图像: {image_path}")

    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法读取图像: {image_path}")
        return

    print(f"图像尺寸: {image.shape}")

    try:
        # 检测面部
        print("检测面部...")
        faces = detector.detect_faces(image)
        print(f"检测到 {len(faces)} 张人脸")

        if len(faces) > 0:
            # 检测关键点
            print("检测关键点...")
            landmarks = detector.detect_landmarks(image, faces)

            # 检测情绪
            print("检测情绪...")
            emotions = detector.detect_emotions(image, faces, landmarks)

            # 检测动作单元(AU)
            print("检测动作单元...")
            aus = detector.detect_aus(image, landmarks)

            # 显示结果
            print("\n检测结果:")
            for i, (face, emotion, au) in enumerate(zip(faces, emotions, aus)):
                print(f"人脸 {i+1}:")

                # 情绪结果
                dominant_emotion = emotion[FEAT_EMOTION_COLUMNS].idxmax()
                emotion_score = emotion[dominant_emotion].values[0]
                print(f"  主要情绪: {dominant_emotion} (置信度: {emotion_score:.2f})")

                # AU结果（显示前5个最活跃的AU）
                au_columns = [col for col in au.columns if col.startswith('AU')]
                top_aus = au[au_columns].mean().sort_values(ascending=False).head(5)
                print("  最活跃的动作单元:")
                for au_name, score in top_aus.items():
                    print(f"    {au_name}: {score:.2f}")

        else:
            print("未检测到人脸，请尝试使用包含更清晰人脸的图像")

    except Exception as e:
        print(f"检测过程中出错: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("PyFeat 检测器测试脚本 - 修复版本")
    print("=" * 50)

    # 设置环境
    model_dir = setup_environment()

    # 初始化检测器
    detector = initialize_detector()
    if detector is None:
        print("无法初始化检测器，可能需要手动下载模型文件")
        print("请检查网络连接，或尝试手动下载模型文件")
        return

    # 测试检测器
    # 您可以提供一个图像路径，或者使用None让脚本创建测试图像
    image_path = None  # 替换为您的图像路径，例如: "path/to/your/image.jpg"
    test_with_sample_image(detector, image_path)

    print("\n测试完成!")
    print(f"模型已保存到: {model_dir}")

if __name__ == "__main__":
    main()