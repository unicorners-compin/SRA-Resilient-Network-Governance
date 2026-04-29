# gemini-advisor

Use this workflow when a task needs Gemini as an external technical advisor.

Requirements:

- `GEMINI_API_KEY` must exist in the environment
- default model:
  - `gemini-3.1-pro-preview`

Use Gemini for:

- hard debugging
- concurrency analysis
- architecture review
- second-opinion reasoning

For multi-turn use:

- send enough context every round
- include prior findings explicitly
- ask concrete next-step questions
