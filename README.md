# Physical AI 2026 Final Project
## LOCAL-FIRST Natural Language Physical AI Robot

自然言語をローカルLLM（Ollama / Qwen2.5 1.5B）が解釈し、
AIが WAVE / POINT_UP / BOW / REST の行動意図を選択します。
ROS 2ノードがその判断を JointTrajectory に変換し、
ros2_control を介して Gazebo 上の CRANE+ V2 を動かします。

### 構成
自然言語
→ Ollama / Qwen2.5 1.5B
→ 行動意図
→ ROS 2
→ JointTrajectory
→ ros2_control
→ Gazebo / CRANE+ V2

### ビルド
```bash
cd ~/pai_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select ai_robot_final
source install/setup.bash
```

### Ollama設定
```bash
export OLLAMA_URL=http://host.docker.internal:11434
export OLLAMA_MODEL=qwen2.5:1.5b
```

### 実行
```bash
ros2 run ai_robot_final ai_robot_controller
```

### 2分自動デモ
```bash
AUTO_DEMO=1 DEMO_SECONDS=120 ros2 run ai_robot_final ai_robot_controller
```
