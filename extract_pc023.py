import re

log_content = ""
with open("C:/Users/youss/.gemini/antigravity-ide/brain/537b42ea-8124-47c1-ae12-68846ff19964/.system_generated/tasks/task-5329.log", "r", encoding="utf-8") as f:
    log_content = f.read()

# The logs are interleaved, but they should be sequential. We want to find the section where it processes PC023.
# Input is "القصه طويل ومملل"
lines = log_content.splitlines()
in_pc023 = False
for line in lines:
    if "القصه طويل ومملل" in line or "القصة طويلة ومملة" in line or "طويل وممل" in line:
        print(line)
