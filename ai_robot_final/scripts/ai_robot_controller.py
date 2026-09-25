#!/usr/bin/env python3
import json, os, re, time, urllib.request
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

VALID = ("WAVE","POINT_UP","BOW","REST","UNKNOWN")

class OllamaClassifier:
    def __init__(self, logger):
        self.logger = logger
        self.url = os.getenv("OLLAMA_URL","http://host.docker.internal:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL","qwen2.5:1.5b")
        with urllib.request.urlopen(self.url + "/api/tags", timeout=5) as r:
            models = [m.get("name","") for m in json.loads(r.read().decode()).get("models",[])]
        if self.model not in models:
            raise RuntimeError(f"Model {self.model} not found. Available: {models}")
        logger.info(f"Ollama connected: {self.url} / model={self.model}")

    def classify(self, command):
        prompt = f'''You are an intent classifier for a CRANE+ V2 robot arm.
Return EXACTLY ONE token: WAVE, POINT_UP, BOW, REST, or UNKNOWN.

WAVE = greeting, hello, wave, say hi
POINT_UP = point upward, ceiling, above
BOW = bow, thank politely
REST = rest, home, neutral
UNKNOWN = anything else

Examples:
こんにちは -> WAVE
こんにちは。元気よく挨拶してください -> WAVE
Hello! Please greet the audience. -> WAVE
上を指してください -> POINT_UP
天井の方向を指して -> POINT_UP
ありがとう。おじぎしてください -> BOW
丁寧にお礼のおじぎをしてください -> BOW
休んでください -> REST
ホームポジションに戻って -> REST

User instruction: {command}
Output only one token.'''
        body = json.dumps({
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.0}
        }).encode()
        req = urllib.request.Request(
            self.url + "/api/generate", data=body,
            headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as r:
            answer = json.loads(r.read().decode()).get("response","").strip().upper()
        for x in VALID:
            if re.search(rf"\b{x}\b", answer):
                return x
        return "UNKNOWN"

class AIRobot(Node):
    def __init__(self):
        super().__init__("ai_robot_controller")
        self.pub = self.create_publisher(
            JointTrajectory, "/crane_plus_arm_controller/joint_trajectory", 10)
        self.joints = ["crane_plus_joint1","crane_plus_joint2",
                       "crane_plus_joint3","crane_plus_joint4"]
        self.get_logger().info("AI Robot Controller started")
        time.sleep(1.0)
        self.ai = OllamaClassifier(self.get_logger())

    def move(self, pos, sec=2.0):
        m = JointTrajectory()
        m.joint_names = self.joints
        p = JointTrajectoryPoint()
        p.positions = [float(v) for v in pos]
        p.velocities = [0.0]*4
        p.accelerations = [0.0]*4
        p.time_from_start = Duration(sec=int(sec), nanosec=int((sec%1)*1e9))
        m.points = [p]
        self.pub.publish(m)
        self.get_logger().info(f"Published JointTrajectory: {pos}")

    def rest(self):
        self.move([0,0,0,0],2.0); time.sleep(2.4)

    def wave(self):
        self.move([0.35,0.25,-0.20,0],2.0); time.sleep(2.2)
        for w in (0.45,-0.45,0.45,-0.45):
            self.move([0.35,0.25,-0.20,w],0.8); time.sleep(0.95)
        self.rest()

    def point_up(self):
        self.move([0,-0.30,0.45,0],2.3); time.sleep(3.2); self.rest()

    def bow(self):
        self.move([0,0.35,-0.30,0],2.0); time.sleep(2.8); self.rest()

    def run_command(self, cmd):
        self.get_logger().info(f'Natural-language command: "{cmd}"')
        intent = self.ai.classify(cmd)
        self.get_logger().info(f"AI decision: {intent}")
        if intent == "WAVE": self.wave()
        elif intent == "POINT_UP": self.point_up()
        elif intent == "BOW": self.bow()
        elif intent == "REST": self.rest()
        else: self.get_logger().warning("UNKNOWN: robot stays still")
        return intent

def interactive(node):
    print("Examples: こんにちは。元気よく挨拶してください / 上を指してください / おじぎしてお礼をしてください / 休んでください / quit")
    while rclpy.ok():
        cmd = input("指示 > ").strip()
        if cmd.lower() in ("quit","exit","q","終了"): break
        if cmd:
            print("AI判定:", node.run_command(cmd))

def auto_demo(node):
    commands = [
        "こんにちは。元気よく挨拶してください。",
        "天井の方向を指してください。",
        "丁寧にお礼のおじぎをしてください。",
        "休んで自然な姿勢に戻ってください。",
        "Hello! Please greet the audience.",
        "上にあるものを示してください。",
        "ありがとう。おじぎしてください。",
        "ホームポジションに戻ってください。"]
    limit = int(os.getenv("DEMO_SECONDS","120"))
    start=time.monotonic(); i=0
    while rclpy.ok() and time.monotonic()-start < limit:
        cmd=commands[i%len(commands)]
        print(f"USER: {cmd}")
        print("AI:", node.run_command(cmd))
        i+=1
    node.rest()

def main():
    rclpy.init()
    node=AIRobot()
    try:
        if os.getenv("AUTO_DEMO","0")=="1": auto_demo(node)
        else: interactive(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
