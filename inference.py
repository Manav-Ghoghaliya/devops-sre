import os
import asyncio
import json
from openai import OpenAI
from client import DevOpsEnvClient
from models import DevOpsAction

# 1. Read the strict environment variables required by the hackathon
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1/")
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Meta-Llama-3-70B-Instruct")
# Notice how HF_TOKEN becomes the API key!
API_KEY = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY") 

# Constants for evaluation
MAX_STEPS = 15
SUCCESS_SCORE_THRESHOLD = 1.0
TASK_NAME = "devops_easy_nginx"
BENCHMARK = "openenv_round1"

# --- STRICT LOGGING FORMATTERS ---
def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: str = None):
    err_str = f" error={error}" if error else ""
    print(f"[STEP] step={step} action={action!r} reward={reward:.2f} done={done}{err_str}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: list):
    print(f"[END] success={success} steps={steps} score={score:.2f} rewards={rewards}", flush=True)
# ---------------------------------

def get_model_message(client: OpenAI, step: int, last_stdout: str, last_stderr: str, pwd: str, history: list) -> str:
    """Calls the LLM to get the next bash command."""
    system_prompt = (
        "You are an expert Linux Site Reliability Engineer. "
        "Your goal is to fix the broken web infrastructure. "
        "Output ONLY a valid JSON object with a single key 'command' containing the bash command to run. "
        "Example: {\"command\": \"systemctl status nginx\"}"
    )
    
    user_prompt = f"Current Directory: {pwd}\nLast Stdout: {last_stdout}\nLast Stderr: {last_stderr}\nWhat is your next command?"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"}, # Forces valid JSON
            temperature=0.2,
            max_tokens=100,
        )
        response_text = completion.choices[0].message.content.strip()
        # Parse the JSON to extract just the command
        command_data = json.loads(response_text)
        return command_data.get("command", "ls -la")
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "ls -la" # Fallback action so the loop doesn't crash

async def main() -> None:
    success = False
    if not API_KEY:
        raise ValueError("Missing HF_TOKEN or OPENAI_API_KEY environment variable.")

    # Initialize the OpenAI Client using the Hugging Face Base URL and Token
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Connect to our local Dockerized environment
    env = DevOpsEnvClient(base_url="http://localhost:8000")

    history = []
    rewards = []
    steps_taken = 0
    score = 0.0

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        last_stdout = result.observation.stdout
        last_stderr = result.observation.stderr
        pwd = result.observation.pwd

        for step in range(1, MAX_STEPS + 1):
            # 1. Get action from LLM
            command = get_model_message(client, step, last_stdout, last_stderr, pwd, history)

            # 2. Execute action in the environment
            action = DevOpsAction(command=command)
            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done

            rewards.append(reward)
            steps_taken = step
            last_stdout = obs.stdout
            last_stderr = obs.stderr
            pwd = obs.pwd

            # 3. Log strictly
            log_step(step=step, action=command, reward=reward, done=done)
            history.append(f"Step {step}: {command!r} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards) / len(rewards) if rewards else 0.0
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as e:
            pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())