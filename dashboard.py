from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import ai_council

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AASM - Autonomous AI Server</title>
        <style>
            body { background: #1a1a1a; color: #00ff00; font-family: monospace; padding: 20px; }
            #console { background: #000; border: 1px solid #333; height: 400px; overflow-y: scroll; padding: 10px; margin-bottom: 20px; }
            input { background: #000; border: 1px solid #00ff00; color: #00ff00; width: 80%; padding: 10px; }
            button { background: #00ff00; color: #000; border: none; padding: 10px 20px; cursor: pointer; }
            .log-entry { margin-bottom: 10px; border-bottom: 1px solid #222; }
            .ai-thought { color: #888; font-style: italic; }
        </style>
    </head>
    <body>
        <h1>Autonomous AI Server Manager</h1>
        <div id="console"></div>
        <input type="text" id="goal" placeholder="Введите задачу для ИИ (напр. 'Установи nginx' или 'Проверь место на диске')">
        <button onclick="sendGoal()">Выполнить</button>

        <script>
            async function sendGoal() {
                const goalInput = document.getElementById('goal');
                const consoleDiv = document.getElementById('console');
                const goal = goalInput.value;
                
                consoleDiv.innerHTML += `<div class='log-entry'><b>User:</b> ${goal}</div>`;
                goalInput.value = '';

                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({goal: goal})
                });
                const data = await response.json();
                
                consoleDiv.innerHTML += `
                    <div class='log-entry'>
                        <div class='ai-thought'>Plan: ${data.plan}</div>
                        <div class='ai-thought'>Critique: ${data.critique}</div>
                        <b>Command:</b> <code>${data.command}</code><br>
                        <b>Result:</b> <pre>${data.output}</pre>
                    </div>
                `;
                consoleDiv.scrollTop = consoleDiv.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/run")
async def run_task(request: Request):
    data = await request.json()
    result = ai_council.run_consensus_task(data['goal'])
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
