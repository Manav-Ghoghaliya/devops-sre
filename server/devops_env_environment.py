import os
import subprocess
from openenv.core.env_server.interfaces import Environment

try:
    from ..models import DevOpsAction, DevOpsObservation, DevOpsState
except ImportError:
    from models import DevOpsAction, DevOpsObservation, DevOpsState

class DevOpsEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = False

    def __init__(self):
        self.task_id = os.environ.get("DEVOPS_TASK", "easy")
        self.pwd = "/root"
        self.steps = 0
        self.max_steps = 15

    def _setup_task(self):
        """Intentionally breaks the system for the agent to fix."""
        if self.task_id == "easy":
            os.system("echo 'server { listen 80; root /var/www/html }' > /etc/nginx/sites-available/default")
            # DOCKER FIX: Kill nginx directly instead of using systemctl
            os.system("nginx -s stop 2>/dev/null || pkill nginx 2>/dev/null || true")
        elif self.task_id == "medium":
            os.system("pm2 stop all 2>/dev/null")
            os.system("echo \"const http = require('http'); http.createServer((req, res) => res.end('OK')).listen(3000);\" > /root/app.js")
        elif self.task_id == "hard":
            os.system("rm -f /etc/ssl/certs/mysite.crt /etc/ssl/private/mysite.key")

    def _evaluate(self) -> float:
        """The Dense Grader: Returns a score between 0.0 and 1.0"""
        score = 0.0
        if self.task_id == "easy":
            # Check 1: Nginx syntax
            if "syntax is ok" in subprocess.run(["nginx", "-t"], capture_output=True, text=True).stderr:
                score += 0.5
            # DOCKER FIX: Check the process list directly instead of systemctl
            if "nginx: master process" in subprocess.run(["ps", "-ef"], capture_output=True, text=True).stdout:
                score += 0.5
        elif self.task_id == "medium":
            if subprocess.run(["pm2", "jlist"], capture_output=True, text=True).stdout.strip() != "[]":
                score += 0.5
            if "OK" in subprocess.run(["curl", "-s", "http://localhost:3000"], capture_output=True, text=True).stdout:
                score += 0.5
        elif self.task_id == "hard":
            if os.path.exists("/etc/ssl/private/mysite.key"): score += 0.3
            if os.path.exists("/etc/ssl/certs/mysite.crt"): score += 0.3
            if score == 0.6: score += 0.4
        return round(score, 2)

    def reset(self) -> DevOpsObservation:
        self.steps = 0
        self.pwd = "/root"
        self._setup_task()
        return DevOpsObservation(
            stdout="Environment initialized. System is degraded.",
            stderr="",
            pwd=self.pwd,
            echoed_message="reset",
            done=False,
            reward=0.0
        )

    def step(self, action: DevOpsAction) -> DevOpsObservation:
        self.steps += 1
        
        # Handle 'cd' commands manually since subprocess is stateless
        if action.command.startswith("cd "):
            target_dir = action.command.split("cd ")[1].strip()
            new_pwd = os.path.abspath(os.path.join(self.pwd, target_dir))
            if os.path.isdir(new_pwd):
                self.pwd = new_pwd
                stdout, stderr = f"Changed directory to {self.pwd}", ""
            else:
                stdout, stderr = "", f"cd: {target_dir}: No such file or directory"
        else:
            try:
                process = subprocess.run(
                    action.command, shell=True, cwd=self.pwd, 
                    capture_output=True, text=True, timeout=10
                )
                stdout, stderr = process.stdout, process.stderr
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "Command timed out."

        reward = self._evaluate()
        done = reward >= 1.0 or self.steps >= self.max_steps
        
        return DevOpsObservation(
            stdout=stdout[:1000], 
            stderr=stderr[:1000], 
            pwd=self.pwd, 
            echoed_message=action.command,
            done=done,
            reward=reward,
            metadata={"status": "Complete" if done else "In Progress"}
        )

    @property
    def state(self) -> DevOpsState:
        return DevOpsState(
            task_id=self.task_id,
            steps_taken=self.steps,
            current_directory=self.pwd,
            current_score=self._evaluate()
        )