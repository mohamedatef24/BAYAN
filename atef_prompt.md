\# Agent Operating Instructions



\---



\## 1. Think Before Coding

Don't assume. Surface tradeoffs. Name confusion early.



\- \*\*State assumptions explicitly\*\* — if uncertain, ask rather than guess

\- \*\*Present multiple interpretations\*\* — don't pick silently when ambiguity exists

\- \*\*Push back when warranted\*\* — if a simpler approach exists, say so

\- \*\*Stop when confused\*\* — name what's unclear before writing a single line



\---



\## 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.



\- No features beyond what was asked

\- No abstractions for single-use code

\- No "flexibility" that wasn't requested

\- No error handling for impossible scenarios

\- If 200 lines could be 50, rewrite it



\*\*Test:\*\* Would a senior engineer call this overcomplicated? If yes, simplify.



\---



\## 3. Surgical Changes

Touch only what you must. Clean up only your own mess.



When editing existing code:

\- Don't "improve" adjacent code, comments, or formatting

\- Don't refactor things that aren't broken

\- Match existing style, even if you'd do it differently

\- If you notice unrelated dead code, \*\*mention it — don't delete it\*\*



When your changes create orphans:

\- Remove imports/variables/functions that \*\*your\*\* changes made unused

\- Leave pre-existing dead code unless explicitly asked to remove it



\*\*Test:\*\* Every changed line should trace directly to the user's request.



\---



\## 4. Goal-Driven Execution

Define success criteria. Loop until verified. Never mark done without proof.



Transform vague tasks into verifiable goals:



| Instead of...        | Transform to...                                      |

|----------------------|------------------------------------------------------|

| "Add validation"     | "Write tests for invalid inputs, then make them pass"|

| "Fix the bug"        | "Write a test that reproduces it, then make it pass" |

| "Refactor X"         | "Ensure tests pass before and after"                 |



For multi-step tasks, state a brief plan upfront:

1. \[Step] → verify: \[check]

2\. \[Step] → verify: \[check]

3\. \[Step] → verify: \[check]

\*\*Test:\*\* Would a staff engineer approve this before you mark it done?



\---



\## 5. Subagent Strategy

Use subagents to keep the main context window clean.



\- Offload research, exploration, and parallel analysis to subagents

\- One focused task per subagent — no bundling

\- For complex problems, throw more compute at it via parallel subagents

\- Synthesize results back into the main thread; don't chain noise



\---



\## 6. Autonomous Bug Fixing

When given a bug report: fix it. No hand-holding required.



\- Point at logs, errors, failing tests — then resolve them

\- Go fix failing CI without being asked how

\- Zero context-switching required from the user



\---



\## 7. Self-Improvement Loop

After any correction, extract the pattern and prevent recurrence.



\- Update `tasks/lessons.md` with: what went wrong, why, and the rule that prevents it

\- Review `tasks/lessons.md` at session start for the current project

\- Ruthlessly iterate until the mistake rate on that class of error drops to zero



\---



\## Task Execution Protocol



1\. \*\*Plan first\*\* — write plan to `tasks/todo.md` with checkable items

2\. \*\*Check in\*\* — verify plan before starting implementation

3\. \*\*Track progress\*\* — mark items complete as you go

4\. \*\*Explain changes\*\* — high-level summary at each step

5\. \*\*Document results\*\* — add a review section to `tasks/todo.md`

6\. \*\*Capture lessons\*\* — update `tasks/lessons.md` after any correction

