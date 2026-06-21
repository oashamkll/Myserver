import requests
import json
import subprocess
import os

import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Пожалуйста, установите переменную окружения OPENROUTER_API_KEY")

MODELS = {
    "generator": "google/gemini-2.0-flash-exp:free",
    "critic": "meta-llama/llama-3.1-8b-instruct:free",
    "finalizer": "mistralai/mistral-7b-instruct:free"
}

def ask_ai(model, prompt, context=""):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a senior linux admin. Output ONLY commands or technical plans."},
                    {"role": "user", "content": f"Context: {context}\n\nTask: {prompt}"}
                ]
            })
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error calling {model}: {str(e)}"

def execute_bash(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except Exception as e:
        return f"Execution error: {str(e)}"

def run_consensus_task(user_goal):
    print(f"[*] Цель: {user_goal}")
    
    # 1. Генерация плана
    plan = ask_ai(MODELS["generator"], f"Create a step-by-step bash plan to: {user_goal}")
    print(f"[1] План от Gemini: {plan[:100]}...")

    # 2. Критика плана
    critique = ask_ai(MODELS["critic"], f"Review this plan for safety and errors. If it's bad, suggest fixes: {plan}")
    print(f"[2] Критика от Llama: {critique[:100]}...")

    # 3. Финальная команда
    final_command = ask_ai(MODELS["finalizer"], f"Based on the plan and critique, provide the FINAL SINGLE BASH COMMAND to achieve the goal. No explanations: Plan: {plan}, Critique: {critique}")
    
    # Очистка команды от markdown (часто ИИ суют в блоки ```bash)
    cmd = final_command.replace("```bash", "").replace("```", "").strip()
    
    print(f"[3] Исполнение команды: {cmd}")
    output = execute_bash(cmd)
    
    return {
        "plan": plan,
        "critique": critique,
        "command": cmd,
        "output": output
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(run_consensus_task(" ".join(sys.argv[1:])))
