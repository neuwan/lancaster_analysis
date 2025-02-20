# -*- coding: utf-8 -*-
"""lancaster_deploy.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1bNQzV7iW33-1I-ddSJeU_tkOMXM4Dqad
"""

import os
import cv2
import zipfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # CORS 활성화 (다른 도메인에서 접근 가능하도록)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
ZIP_FOLDER = "zip_files"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload_multiple_files():

    if "file" not in request.files:
        return jsonify({"error": "파일이 없습니다."}), 400

    files = request.files.getlist("file")  # ✅ 여러 개의 파일을 가져옴
    if not files:
        return jsonify({"error": "업로드된 파일이 없습니다."}), 400

    result_files = []  # 압축할 결과 파일 리스트
    analysis_results = []

    # ✅ CSV 헤더 추가 (한 번만 실행)
    analysis_results.append("파일명, 빨간면적, 파란면적, 교차면적, 빨강skew, 파랑skew, 빨강각도1, 빨강각도2, 빨강각도3, 빨강각도4, 빨강각도5, 빨강각도6, 빨강각도7, 빨강각도8, 빨강각도9, 파랑각도1, 파랑각도2, 파랑각도3, 파랑각도4, 파랑각도5, 파랑각도6, 파랑각도7, 파랑각도8, 파랑각도9")

    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)  # ✅ 파일 저장

        try:
            result_txt, result_img1, result_img2 = image_process(file_path)  # ✅ 파일 처리
            result_img1_path = os.path.join(RESULT_FOLDER, f"processed_1_{filename}")
            result_img2_path = os.path.join(RESULT_FOLDER, f"processed_2_{filename}")
            print("")

            cv2.imwrite(result_img1_path, result_img1)  # ✅ 결과 이미지 1 저장
            result_img2.savefig(result_img2_path , dpi=300, bbox_inches='tight')
            analysis_results.append(result_txt)  # ✅ 텍스트 데이터 저장 (파일이 아니라 문자열 추가)

            result_files.extend([result_img1_path, result_img2_path])  # ✅ 결과 파일 리스트 추가

            # ✅ 원본 파일 삭제
            os.remove(file_path)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ✅ 전체 분석 결과를 하나의 TXT 파일로 저장
    result_txt_path = os.path.join(RESULT_FOLDER, "final_analysis.txt")
    with open(result_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis_results))  # ✅ 분석 결과 저장

    result_files.append(result_txt_path)  # ✅ 결과 파일 리스트에 추가 (이제 정상적으로 추가 가능)

    # 🔹 ZIP 파일로 압축
    zip_filename = "processed_results.zip"
    zip_path = os.path.join(ZIP_FOLDER, zip_filename)

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in result_files:
            zipf.write(file, os.path.basename(file))  # ✅ 결과 파일을 ZIP에 추가

    return jsonify({
        "message": f"{len(files)}개의 파일이 처리되었습니다!",
        "zip_file": zip_filename
    })

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    zip_path = os.path.join(ZIP_FOLDER, filename)
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True)
    return jsonify({"error": "파일을 찾을 수 없습니다."}), 404


def home():
    return render_template("index.html")  

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
"""
port = 5000
public_url = ngrok.connect(port).public_url
print(f"🚀 ngrok URL: {public_url}")
app.run(port=port)"""

def image_process(filename):
  from sklearn.cluster import KMeans
  import numpy as np
  from scipy.spatial import ConvexHull
  from shapely.geometry import Polygon
  import matplotlib.pyplot as plt
  from math import atan2
  import os
  import cv2

  ############################################################################
  # 1. 이미지를 로드
  image = cv2.imread(filename)

  image_rgb = image
  img0=image
############################################################################
  # 2. 이미지에서 blue, red color 추출

  # 이미지의 각 픽셀에서 RGB 값을 추출
  # RGB 값을 저장할 리스트를 초기화
  rgb_values = []

  # 이미지의 각 픽셀을 순회하면서 RGB 값을 추출
  for row in range(image_rgb.shape[0]):
      for col in range(image_rgb.shape[1]):
          rgb_values.append((col, row, image_rgb[row, col]))

  # RGB 값이 서로 다른 픽셀 값만 필터링
  unique_rgb_values = [value for value in rgb_values if len(set(value[2])) > 1]

  # RGB 값이 빨간색 또는 파란색에 가까운지를 판단하기 위한 임계값을 정의
  # 이 임계값은 색상이 특정 색에 가깝다고 판단할 수 있는 최소한의 차이를 의미
  color_threshold = 60

############################################################################

  # 3. 빨간색 점들과 파란색 점들을 분류
  red_points = []
  blue_points = []

  for value in unique_rgb_values:
      x, y, rgb = value
      b, g, r = rgb
      # R 값이 G와 B 값보다 color_threshold 이상 높으면 빨간색으로 판단
      if r > g + color_threshold and r > b + color_threshold:
          red_points.append((x, y))
      # B 값이 R과 G 값보다 color_threshold 이상 높으면 파란색으로 판단
      elif b > r + color_threshold and b > g + color_threshold:
          blue_points.append((x, y))


  # 빨간색 점들을 9개의 클러스터로 분류
  red_points_array = np.array(red_points)
  kmeans_red = KMeans(n_clusters=9, random_state=0).fit(red_points_array)
  red_labels = kmeans_red.labels_


  # 파란색 점들을 9개의 클러스터로 분류
  blue_points_array = np.array(blue_points)
  kmeans_blue = KMeans(n_clusters=9, random_state=0).fit(blue_points_array)
  blue_labels = kmeans_blue.labels_

  # 클러스터링 결과를 이용해 각 클러스터의 점들을 분류
  red_clusters = [[] for _ in range(9)]
  for point, label in zip(red_points, red_labels):
      red_clusters[label].append(point)

  blue_clusters = [[] for _ in range(9)]
  for point, label in zip(blue_points, blue_labels):
      blue_clusters[label].append(point)

  # 각 클러스터의 점 개수를 확인
  red_cluster_sizes = [len(cluster) for cluster in red_clusters]
  blue_cluster_sizes = [len(cluster) for cluster in blue_clusters]
############################################################################
# 4. 빨간 점과 파란 점의 중심점 계산

  # 각 클러스터의 중심 좌표를 계산
  red_cluster_centers = []
  blue_cluster_centers = []

  # 빨간색 클러스터 중심 좌표 계산
  for cluster in red_clusters:
      x_center = (np.mean([point[0] for point in cluster]))
      y_center = (np.mean([point[1] for point in cluster]))
      x_center = round(x_center,2)
      y_center = round(y_center,2)

      red_cluster_centers.append((x_center, y_center))

  # 파란색 클러스터 중심 좌표 계산
  for cluster in blue_clusters:
      x_center = (np.mean([point[0] for point in cluster]))
      y_center = (np.mean([point[1] for point in cluster]))
      x_center = round(x_center,2)
      y_center = round(y_center,2)
      blue_cluster_centers.append((x_center, y_center))


  # 원본 이미지를 다시 로드하여 클러스터 중심에 점을 표시
  image_with_cluster_centers = image.copy()

  # 빨간색 클러스터 중심을 보라색 점으로 표시
  for i, center in enumerate(red_cluster_centers):
      cv2.circle(image_with_cluster_centers, (int(center[0]), int(center[1])), 5, (255, 0, 255), -1)
      cv2.putText(image_with_cluster_centers, str(i+1), (int(center[0]), int(center[1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 3)

  # 파란색 클러스터 중심을 초록색 점으로 표시
  for i, center in enumerate(blue_cluster_centers):
      cv2.circle(image_with_cluster_centers, (int(center[0]), int(center[1])), 5, (0, 255, 0), -1)
      cv2.putText(image_with_cluster_centers, str(i+1), (int(center[0]), int(center[1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 155, 100), 3)

  #첫 번째 이미지
  #cv2_imshow(image_with_cluster_centers)
  img1=image_with_cluster_centers
  #image_with_cluster_centers_path = '1. image_with_cluster_centers.png'
  #cv2.imwrite(image_with_cluster_centers_path, image_with_cluster_centers)


############################################################################


#5. 파란과 붉은 점으로 이루어진 면적 시각화

  # 원본 이미지를 다시 로드하고 마스크를 다시 생성
  image_red=image.copy()
  mask = np.zeros_like(image_red)
  red_hull = ConvexHull(np.array(red_cluster_centers))

  # BGR 순서로 빨간색 색상을 지정하여 마스크에 색칠
  cv2.fillConvexPoly(mask, np.array([red_cluster_centers[i] for i in red_hull.vertices], dtype=np.int32), (0, 0, 255))

  # 원본 이미지에 마스크를 투명하게 겹쳐서 추가.  alpha값을 조정하여 투명도를 결정
  alpha=1.0
  red_mask = cv2.addWeighted(mask, alpha, image_red, 0.7, 0, image_red)
  #두번째 이미지 (빨간 마스크)
  #cv2_imshow(red_mask)
  img2=red_mask


  # 올바른 색상으로 투명하게 색칠된 이미지를 저장
  #image_with_correct_translucent_red_hull_path = '2. image_with_correct_translucent_red_hull.png'
  #cv2.imwrite(image_with_correct_translucent_red_hull_path, image_red)

  #image_with_correct_translucent_red_hull_path



  # 원본 이미지를 다시 로드하고 마스크를 다시 생성
  blue_image=image.copy()
  mask2 = np.zeros_like(blue_image)
  blue_hull = ConvexHull(np.array(blue_cluster_centers))

  # BGR 순서로 빨간색 색상을 지정하여 마스크에 색칠
  cv2.fillConvexPoly(mask2, np.array([blue_cluster_centers[i] for i in blue_hull.vertices], dtype=np.int32), (255, 0, 0))

  # 원본 이미지에 마스크를 투명하게 겹쳐서 추가 alpha값을 조정
  alpha=1.0
  blue_mask = cv2.addWeighted(mask2, alpha, blue_image, 0.7, 0, blue_image)
  #세번째 이미지, 파란 마스크
  #cv2_imshow(blue_mask)
  img3=blue_mask

  from scipy.spatial import ConvexHull
  import numpy as np

  # Convex Hull을 구하고 면적을 계산
  red_hull = ConvexHull(np.array(red_cluster_centers))
  blue_hull = ConvexHull(np.array(blue_cluster_centers))

  red_hull_area = red_hull.volume  # ConvexHull에서는 2D에서의 면적이 'volume' 속성에 저장됩니다.
  blue_hull_area = blue_hull.volume

  #print("붉은영역 면적 : "+str(round(red_hull_area, 2))+" 파란 영역 면적 : "+str(round(blue_hull_area,2)) )
############################################################################
#6. 찌그러진 정도 확인 위한 정사각형 찾기

  def distance_and_points(redOrblue):
    # 거리와 좌표 쌍을 저장할 리스트 초기화
    distances_with_points = []
    # 모든 가능한 좌표 쌍에 대해 거리를 계산
    for i in range(len(redOrblue)):
        for j in range(i + 1, len(redOrblue)):
            point1 = redOrblue[i]
            point2 = redOrblue[j]
            distance = np.linalg.norm(np.array(point1) - np.array(point2))
            distances_with_points.append((distance, point1, point2))


    # 거리에 따라 내림차순으로 정렬
    distances_with_points.sort(reverse=True, key=lambda x: x[0])

    # 가장 긴 거리와 두 번째로 긴 거리를 만드는 좌표 쌍 추출
    longest_distance_pair = distances_with_points[0]
    second_longest_distance_pair = distances_with_points[1]

    #print("가장 긴 거리를 만드는 좌표 쌍:", longest_distance_pair)
    #print("두 번째로 긴 거리를 만드는 좌표 쌍:", second_longest_distance_pair)

    rtg_wall = (second_longest_distance_pair[0] / (2**0.5) )
    #print("작은 대각선으로 만들어지는 정사각형의 한 변 길이 : ", rtg_wall)
    rtg_area = rtg_wall**2
    #print("작은 대각선으로 만들어지는 정사각형의 넓이 : ", rtg_area,"\n\n")
    return (second_longest_distance_pair, rtg_area)



  #print("빨간 점들 : ")
  red_index = distance_and_points(red_cluster_centers)
  red_rtg_area = red_index[1]
  #print("파란 점들 : ")
  blue_index = distance_and_points(blue_cluster_centers)
  blue_rtg_area = blue_index[1]



  #print("찌그러진 정도 - 빨간 면적 - 빨간정사각형 :", red_hull_area-red_rtg_area )
  #print("찌그러진 정도 - 파란 면적 - 파란정사각형 :", blue_hull_area-blue_rtg_area )


  #print("빨간 대각선 좌표 두개는 : ",red_index[0][1],"and ",red_index[0][2])
  red_diag_point = (red_index[0][1] , red_index[0][2])
  #print("파란 대각선 좌표 두개는 : ",blue_index[0][1],"and ",blue_index[0][2])
  blue_diag_point = (blue_index[0][1] , blue_index[0][2])

  #대각선을 이루는 두 점을 알려줬을 때 남은 꼭지점의 좌표를 반환하는 함수
  def find_square_vertices(point1, point2):
    #print(point1)
    #print(point2)

    x1=point1[0]
    y1=point1[1]

    x2=point2[0]
    y2=point2[1]

    #print("x1은",x1, "y1은 : ",y1, " x2 : ", x2, "y2 : ",y2)

    if (x1>x2 and y1>y2 ) or (x2>x1 and y2>y1):
      #우상향 대각선인 경우
      #좌측 위 점의 좌표 구하기 (낮은 x값, 높은 y값)
      LtUp_dot = (min(x1, x2) , max(y1,y2))
      #print("좌측 위 점의 좌표는 : ", LtUp_dot)
      #우측 위 점의 좌표 구하기 (높은 x값, 높은 y값)
      RtUp_dot = (max(x1, x2), max(y1, y2))
      #print("우측 상단 점의 좌표는 : ", RtUp_dot)
      #우측 하단 점의 좌표 구하기 (높은 x값, 낮은 y값)
      RtDn_dot = (max(x1, x2), min(y1, y2))
      #print("우측 하단 점의 좌표는 : ", RtDn_dot)
      #좌측 하단 점의 좌표 구하기 (낮은 x값, 낮은 y값)
      LtDn_dot = (min(x1, x2), min(y1,y2))
      #print("좌측 하단 점의 좌표는 : " ,LtDn_dot)

      #좌상단 - 우상단 - 우하단 - 좌하단 순서로 배열
      #print( LtUp_dot, RtUp_dot, RtDn_dot, LtDn_dot   )
      vertices = (LtUp_dot, RtUp_dot, RtDn_dot, LtDn_dot)
      return vertices

    else:
      #우하향 대각선인 경우
      #좌측 위 점의 좌표 구하기
      LtUp_dot = (min(x1, x2), max(y1,y2))
      #좌측 하단 점의 좌표 구하기 (낮은 x값, 낮은 y값)
      LtDn_dot = (min(x1,x2), min(y1, y2))
      #print("좌측 하단 점의 좌표는 : ", LtDn_dot)
      #우측 상단 점의 좌표 구하기
      RtUp_dot = (max(x1,x2), max(y1, y2))
      #print("우측 상단 점의 좌표는 : ", RtUp_dot)
      #우측 하단 점의 좌표 구하기
      RtDn_dot = (max(x1,x2)), min(y1,y2)

        #좌상단 - 우상단 - 우하단 - 좌하단 순서로 배열

      #print(LtUp_dot, RtUp_dot, RtDn_dot, LtDn_dot )
      vertices = (LtUp_dot, RtUp_dot, RtDn_dot, LtDn_dot)
      return vertices

  find_square_vertices( red_diag_point[0], red_diag_point[1]  )

  vertices=find_square_vertices( red_diag_point[0], red_diag_point[1]  )
  square_coords = np.array(vertices, dtype=np.int32)
  square_coords = square_coords.reshape((-1, 1, 2))  # cv2.polylines 함수에 맞게 좌표 형태를 변환

  mask = np.zeros_like(image_red)
########################################################################################################
  # 7. 사각형 그리기 및 색칠하기 _ red
  # image_red는 이미 생성된 cv2 이미지 객체
  # cv2.fillPoly 함수를 사용하여 사각형 내부를 노란색으로 채움 (노란색: (0, 255, 255) in BGR)
  cv2.fillPoly(mask, [square_coords], (0, 255, 255))

  # 원본 이미지와 마스크 블렌딩
  alpha = 0.7  # 투명도 설정
  image_blend = cv2.addWeighted(image_red, 0.8, mask, alpha, 0)
# 4번째 이미지 : skewness_red
  #cv2_imshow(image_blend)
  img4=image_blend


  vertices=find_square_vertices( blue_diag_point[0], blue_diag_point[1]  )
  square_coords = np.array(vertices, dtype=np.int32)
  square_coords = square_coords.reshape((-1, 1, 2))  # cv2.polylines 함수에 맞게 좌표 형태를 변환

  mask2 = np.zeros_like(blue_image)

  # 사각형 그리기 및 색칠하기 _ blue
  # image_red는 이미 생성된 cv2 이미지 객체
  # cv2.fillPoly 함수를 사용하여 사각형 내부를 노란색으로 채움 (노란색: (0, 255, 255) in BGR)
  cv2.fillPoly(mask2, [square_coords], (0, 255, 255))

  # 원본 이미지와 마스크 블렌딩
  alpha = 0.4  # 투명도 설정
  image_blend2 = cv2.addWeighted(blue_image, 1-alpha, mask2, alpha, 0)
#5번째 이미지 : skewness_blue
  #cv2_imshow(image_blend2)
  img5=image_blend2

###################################################################################3
#8. octagon 함수 이용 위한 전처치 및 octagon 함수 이용


  #y좌표 보정 (이미지 파일은 y좌표가 위에서 부터 0, 일반 좌표계는 y좌표가 아래에서부터 0)
  #본래 이미지에서 y축 최대길이 확인
  y_axis_max = image.shape[1]
  #새로운 변수에 저장 (각 클러스터별 중심좌표 )
  new_red = [(x, y_axis_max - y) for x, y in red_cluster_centers]
  new_blue = [(x, y_axis_max - y) for x, y in blue_cluster_centers]

  def delete_center(centers):
    points = np.array(centers)
    #print(points)

    # 각 점의 x, y 좌표의 평균을 계산
    x_mean = np.mean(points[:, 0])
    y_mean = np.mean(points[:, 1])

    distance = []

    for point in points:
      distance.append( (point[0]-x_mean)**2 + (point[1]-y_mean)**2 )

    #print(distance)
    min_index = np.argmin(distance)
    #print("가장 작은 인덱스는 : ", min_index)

    return min_index

  red_center_index = delete_center(new_red)
  del new_red[red_center_index]
  #print("중앙점이 제거된 빨간점 좌표 : ",new_red)

  blue_center_index = delete_center(new_blue)
  del new_blue[blue_center_index]
  #print("중앙점이 제거된 파란점 좌표 : ",new_blue)

  def vertices_order(cluster):
    # 주어진 8각형 꼭짓점 좌표들
    octagon_vertices = cluster

    # 꼭짓점들의 중심점(centroid) 계산
    centroid = np.mean(octagon_vertices, axis=0)

    # 각 꼭짓점과 중심점 사이의 각도 계산
    def angle_from_centroid(vertex, centroid):
        return atan2(vertex[1] - centroid[1], vertex[0] - centroid[0])

    # 중심점으로부터의 각도에 따라 꼭짓점들 정렬
    sorted_vertices = sorted(octagon_vertices, key=lambda vertex: angle_from_centroid(vertex, centroid))

    # 순서대로 배치된 꼭짓점 좌표 출력
    #print("Sorted vertices:", sorted_vertices)
    return sorted_vertices

  red_sorted=vertices_order(new_red)
  blue_sorted=vertices_order(new_blue)

  # red_cluster_centers와 blue_cluster_centers 변수에 저장된 좌표값으로 두 다각형 생성
  red_polygon = Polygon(red_sorted)
  blue_polygon = Polygon(blue_sorted)

  # 두 다각형의 교차 부분 계산
  intersection_polygon = red_polygon.intersection(blue_polygon)

  # 교차하는 다각형의 면적 계산
  intersection_area = intersection_polygon.area

  #print("교차하는 부분의 면적:", intersection_area)

  # matplotlib을 사용하여 두 개의 8각형 도형 그리기
  fig, ax = plt.subplots()

  octagon1=red_polygon
  octagon2=blue_polygon

  # 첫 번째 8각형 도형: 투명한 빨간색으로 색칠
  x1, y1 = octagon1.exterior.xy
  ax.fill(x1, y1, alpha=0.5, fc='red', ec='none')

  # 두 번째 8각형 도형: 투명한 파란색으로 색칠
  x2, y2 = octagon2.exterior.xy
  ax.fill(x2, y2, alpha=0.5, fc='blue', ec='none')

#6번째 이미지 : 겹치는 옥타곤

  # 그래프 설정
  ax.set_title('Two Octagons')
  plt.xlabel('X Coordinate')
  plt.ylabel('Y Coordinate')
  plt.axis('equal')
  plt.grid(True)
  #plt.savefig(filename+"_overlapping_area.png", dpi=300, bbox_inches='tight')


###################################################################################3
#9. 각도 계산 by PCA

  def point_angle(point):
    points = np.array(point)
    # 데이터의 평균 계산
    mean = np.mean(points, axis=0)
    # 데이터 중심화
    centered_points = points - mean
    # 공분산 행렬 계산
    cov_matrix = np.cov(centered_points, rowvar=False)
    # 고유값과 고유벡터 계산
    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
    # 가장 큰 고유값에 해당하는 고유벡터 선택 (주성분)
    principal_component = eigenvectors[:, np.argmax(eigenvalues)]
    # 주성분 벡터와 x축 사이의 각도 계산
    angle_rad = np.arctan2(principal_component[1], principal_component[0])
    angle_deg = round(abs(np.degrees(angle_rad)), 2)
    #print(f"기울어진 각도: {angle_deg:.2f}도")
    return angle_deg

  #for i, cluster in enumerate(red_clusters):
    #print("빨간 점의 "+str(i+1)+"번째 선의 기울어진 각도 : "+str(point_angle(cluster)))

  #for i, cluster in enumerate(blue_clusters):
    #print("파란 점의 "+str(i+1)+"번째 선의 기울어진 각도 : "+str(point_angle(cluster)))


###################################################################################3
#10. 최종 결론

  #총픽셀면적
  total_pixel=image.shape[0]*image.shape[1]
  #print(image.shape[0]*image.shape[1])
  #실제 란카스터 면적 80 * 80

  # 계산된픽셀면적 / 총 픽셀면적 = 실제 면적 / 실제 총 면적
  #실제 면적 = 계산된픽셀면적 * (실제총면적/총픽셀면적)
  gyesu=6400/total_pixel

  ##최종 결론

  #print("모든 단위는 cm^2입니다.")
  #print("붉은영역 면적 : "+str(round(red_hull_area*gyesu, 2)))
  #print("파란 영역 면적 : "+str(round(blue_hull_area*gyesu,2)) )
  #print("교차하는 부분의 면적:", round(intersection_area*gyesu,2))

  #print("빨간 skew :", round( (red_hull_area-red_rtg_area)*gyesu ,2) )
  #print("파랑 skew :", round ( (blue_hull_area-blue_rtg_area)*gyesu ,2) )

  row1 = cv2.hconcat([img0, img1, img2])
  row2 = cv2.hconcat([img3, img4, img5])
  combined = cv2.vconcat([row1, row2])
  #cv2_imshow(combined)
  #cv2.imwrite(filename+"_analysis_process.png", combined)

  final_redarea=str(round(red_hull_area*gyesu, 2))
  final_bluearea=str(round(blue_hull_area*gyesu, 2))
  final_intersectarea=str(round(intersection_area*gyesu,2))
  final_skew_red=str(round( (red_hull_area-red_rtg_area)*gyesu,2))
  final_skew_blue=str(round( (blue_hull_area-blue_rtg_area)*gyesu,2))

  #final_result="모든 단위는 cm^2입니다. 빨간면적: "+final_redarea+" 파란면적: "+final_bluearea+" 교차면적: "+final_intersectarea+" 빨강skew: "+final_skew_red+" 파랑skew: "+final_skew_blue
  #print(final_result)

  red_angle_result = []
  blue_angle_result = []

  for i, cluster in enumerate(red_clusters):
    #print("빨간 점의 "+str(i+1)+"번째 선의 기울어진 각도 : "+str(point_angle(cluster)))
    red_angle_result.append((point_angle(cluster)))
  for i, cluster in enumerate(blue_clusters):
    #print("파란 점의 "+str(i+1)+"번째 선의 기울어진 각도 : "+str(point_angle(cluster)))
    blue_angle_result.append((point_angle(cluster)))

  my_list = [1, 2, 3, 4]
  red_angle_result = ", ".join(map(str, red_angle_result))
  blue_angle_result = ", ".join(map(str, blue_angle_result))

  output = (filename+", "+final_redarea+", "+final_bluearea+", "+final_intersectarea+", "+final_skew_red+", "+
            final_skew_blue + ", " + red_angle_result + ", " +blue_angle_result )
  return [output, combined, fig]
